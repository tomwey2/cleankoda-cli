import asyncio
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable

import litellm
from litellm import stream_chunk_builder
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
)

if TYPE_CHECKING:
    from cleankoda.session_state import SessionState, StatusManager

from cleankoda.tools import TOOL_SCHEMAS, run_tool

litellm.suppress_debug_info = True


def is_cold_start_error(e: Exception) -> bool:
    """Prüft, ob ein Fehler auf einen Serverless Cold Start / ein ladendes Modell hindeutet."""
    if isinstance(e, (ServiceUnavailableError, APIConnectionError, APIError)):
        msg = str(e).lower()
        status_code = getattr(e, "status_code", None)
        if status_code == 503:
            return True
        keywords = [
            "loading model",
            "model is loading",
            "service unavailable",
            "cold start",
            "503",
            "starting up",
        ]
        return any(kw in msg for kw in keywords)
    return False


def format_tool_call_display(func_name: str, func_args: Any) -> str:
    """Format function name and primary parameter for display."""
    import json

    args_dict = {}
    if isinstance(func_args, str):
        try:
            args_dict = json.loads(func_args) if func_args else {}
        except Exception:
            args_dict = {}
    elif isinstance(func_args, dict):
        args_dict = func_args

    if not isinstance(args_dict, dict):
        return f"{func_name}({func_args})"

    path_val = args_dict.get("path") or args_dict.get("file_path") or args_dict.get("filepath")
    if path_val:
        return f"{func_name}({path_val})"

    if "command" in args_dict:
        return f"{func_name}({args_dict['command']})"

    if "url" in args_dict:
        return f"{func_name}({args_dict['url']})"

    if len(args_dict) == 1:
        val = next(iter(args_dict.values()))
        return f"{func_name}({val})"

    if isinstance(func_args, str) and func_args:
        return f"{func_name}({func_args})"

    return f"{func_name}()"


def _clear_llm_status(
    status_manager: "StatusManager | None",
) -> None:
    """Helper to clear active LLM status indicators."""
    if status_manager:
        status_manager.clear("llm")


async def _wait_for_cold_start(
    provider: str,
    attempt: int,
    max_attempts: int,
    initial_delay: float,
    status_manager: "StatusManager | None",
    cancel_event: asyncio.Event | None,
) -> tuple[list[str], bool]:
    """Handles cold start status notifications, exponential backoff delay, and cancellation checks.

    Args:
        provider: Provider name string (e.g. 'mistral').
        attempt: Current retry attempt index (1-based).
        max_attempts: Maximum allowed retries.
        initial_delay: Base delay in seconds.
        status_manager: Optional StatusManager instance.
        cancel_event: Optional asyncio.Event to trigger early abort.

    Returns:
        tuple[list[str], bool]: Messages to yield to the caller, and boolean `should_retry`.
    """
    if attempt > max_attempts:
        err_msg = f"LLM could not be started after {max_attempts} attempts."
        _clear_llm_status(status_manager)
        return [f"[LLM Error ({provider}): {err_msg}]\n"], False

    # Calculate exponential backoff delay (10s, 20s, 40s, ...)
    current_delay = initial_delay * (2 ** (attempt - 1))
    status_text = (
        f"LLM Cold Start: attempt {attempt}/{max_attempts} ({int(current_delay)}s) [Esc to cancel]"
    )

    if status_manager:
        status_manager.set("llm", status_text)

    output_messages: list[str] = []
    if not status_manager:
        output_messages.append(f"[yellow]⟳ {status_text}[/yellow]\n")

    # Wait for delay or handle cancel_event
    if cancel_event is not None:
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=current_delay)
            _clear_llm_status(status_manager)
            output_messages.append("[yellow]LLM startup aborted.[/yellow]\n")
            return output_messages, False
        except asyncio.TimeoutError:
            pass
    else:
        await asyncio.sleep(current_delay)

    return output_messages, True


async def stream_llm_completion(
    messages: list[dict[str, Any]] | Any,
    state: "SessionState | Any",
    tools: list[dict[str, Any]] | None = TOOL_SCHEMAS,
    cancel_event: asyncio.Event | None = None,
    status_manager: "StatusManager | None" = None,
    initial_delay: float = 10.0,
    max_attempts: int = 10,
    chunks_out: list[Any] | None = None,
) -> AsyncGenerator[str, None]:
    """Streams single-turn completion responses from LiteLLM.

    Handles provider configuration, API key resolution, streaming token delivery,
    automatic exponential backoff retries on serverless cold starts, and error handling.

    Args:
        messages: Conversation history (list of message dicts or Memory object).
        state: Active SessionState configuration (provider, model, temperature, etc.).
        tools: Optional list of tool schemas for function calling.
        cancel_event: Optional asyncio.Event to trigger early cancellation during retries.
        status_manager: Optional StatusManager for updating UI status slots.
        initial_delay: Base delay in seconds for exponential backoff during cold starts.
        max_attempts: Maximum retry attempts for cold start errors.
        chunks_out: Optional list into which raw LiteLLM stream chunks will be collected.

    Yields:
        str: Streaming content tokens, status update messages, or error descriptions.
    """
    litellm.suppress_debug_info = True

    from cleankoda.llm.config import get_provider_config

    # --- Step 1: Provider and API configuration ---
    provider_name = getattr(state, "provider", "mistral")
    provider_config = get_provider_config(provider_name)

    model_identifier = state.litellm_model_identifier
    api_key = state.get_active_api_key()

    if hasattr(messages, "messages"):
        msg_list = messages.messages
    elif isinstance(messages, list):
        msg_list = messages
    else:
        msg_list = list(messages)

    kwargs: dict[str, Any] = {
        "model": model_identifier,
        "messages": msg_list,
        "temperature": getattr(state, "temperature", 0.2),
        "max_tokens": getattr(state, "max_tokens", 4096),
        "stream": True,
    }

    if provider_config and provider_config.api_base:
        kwargs["api_base"] = provider_config.api_base

    if tools:
        kwargs["tools"] = tools

    if api_key:
        kwargs["api_key"] = api_key
    elif provider_config and (provider_config.api_base or provider_config.is_custom or not provider_config.requires_api_key):
        kwargs["api_key"] = "dummy"

    # --- Step 2: Retry Loop for LiteLLM Completion & Cold Starts ---
    attempt = 0
    model_ready_notified = False

    while True:
        try:
            # Initiate streaming completion via LiteLLM (`acompletion` returns an async generator of stream chunks)
            if status_manager:
                status_manager.set("llm", "call llm")
            response = await litellm.acompletion(**kwargs)

            # Iterate through incoming streaming chunks as they arrive from the LLM provider
            async for chunk in response:
                if not chunk:
                    continue

                # Each chunk contains a list of 'choices' (completion candidates, typically 1 candidate at index 0)
                choices = getattr(chunk, "choices", None) or (chunk.get("choices") if isinstance(chunk, dict) else None)
                if not choices:
                    continue

                # Store the raw stream chunk if caller (e.g. run_agent) provided a collector list for tool-call reconstruction
                if chunks_out is not None:
                    chunks_out.append(chunk)

                # Extract the primary candidate (index 0)
                first_choice = choices[0]

                # 'delta' holds the incremental payload update (new text token, tool call fragment, etc.) for this chunk
                delta = getattr(first_choice, "delta", None) or (first_choice.get("delta") if isinstance(first_choice, dict) else None)
                if not delta:
                    continue

                # Extract the incremental text content token string if available
                content = getattr(delta, "content", None) or (delta.get("content") if isinstance(delta, dict) else None)
                if content:
                    # Notify user if model succeeded after a cold start retry
                    if attempt > 0 and not model_ready_notified:
                        if status_manager:
                            status_manager.clear("llm")
                        else:
                            yield "[green]✔ Model ready.[/green]\n"
                        model_ready_notified = True

                    # Yield content token immediately to stream it live to UI / CLI
                    yield content

            _clear_llm_status(status_manager)
            break

        # --- Step 3: Error Handling & Cold Start Retries ---
        except AuthenticationError as e:
            _clear_llm_status(status_manager)
            yield f"[Authentication Error ({state.provider}): Please check your API key. Details: {e}]"
            return
        except RateLimitError as e:
            _clear_llm_status(status_manager)
            yield f"[Rate Limit Exceeded ({state.provider}): {e}]"
            return
        except (ServiceUnavailableError, APIConnectionError, APIError) as e:
            if is_cold_start_error(e):
                attempt += 1
                messages_to_yield, should_retry = await _wait_for_cold_start(
                    provider=getattr(state, "provider", "mistral"),
                    attempt=attempt,
                    max_attempts=max_attempts,
                    initial_delay=initial_delay,
                    status_manager=status_manager,
                    cancel_event=cancel_event,
                )
                for msg in messages_to_yield:
                    yield msg
                if not should_retry:
                    return
            else:
                _clear_llm_status(status_manager)
                if isinstance(e, (APIConnectionError, ServiceUnavailableError)):
                    yield f"[Connection Error ({state.provider}): Unable to reach server. {e}]"
                else:
                    yield f"[LLM Error ({state.provider}): {e}]"
                return
        except Exception as e:
            _clear_llm_status(status_manager)
            yield f"[Unexpected Error ({state.provider}): {type(e).__name__} - {e}]"
            return
