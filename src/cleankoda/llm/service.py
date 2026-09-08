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


async def stream_chat_response(
    messages: list[dict[str, Any]] | Any,
    state: "SessionState | Any",
    tools: list[dict[str, Any]] | None = TOOL_SCHEMAS,
    cancel_event: asyncio.Event | None = None,
    status_callback: Callable[[str | None], None] | None = None,
    status_manager: "StatusManager | None" = None,
    initial_delay: float = 10.0,
    max_attempts: int = 10,
) -> AsyncGenerator[str, None]:
    """Streamt Antworten von LiteLLM basierend auf dem angegebenen SessionState und führt ggf. Tool-Calls aus.
    Unterstützt automatische Retries bei Cold Starts mit exponentiellem Backoff, StatusManager/Status-Callbacks und Abbruch per cancel_event.
    """
    litellm.suppress_debug_info = True

    from cleankoda.llm.config import get_provider_config

    provider_name = getattr(state, "provider", "mistral")
    provider_config = get_provider_config(provider_name)

    model_identifier = state.litellm_model_identifier
    api_key = state.get_active_api_key()

    if hasattr(messages, "messages"):
        memory_obj = messages
        msg_list = messages.messages
    elif isinstance(messages, list):
        memory_obj = None
        msg_list = messages
    else:
        memory_obj = None
        msg_list = list(messages)

    max_tool_iterations = 10
    iteration = 0

    while iteration < max_tool_iterations:
        iteration += 1

        current_messages = memory_obj.messages if memory_obj is not None else msg_list

        kwargs: dict[str, Any] = {
            "model": model_identifier,
            "messages": current_messages,
            "temperature": state.temperature,
            "max_tokens": state.max_tokens,
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

        chunks = []
        attempt = 0
        model_ready_notified = False

        while True:
            try:
                response = await litellm.acompletion(**kwargs)
                async for chunk in response:
                    if not chunk:
                        continue
                    choices = getattr(chunk, "choices", None) or (chunk.get("choices") if isinstance(chunk, dict) else None)
                    if not choices:
                        continue
                    chunks.append(chunk)
                    first_choice = choices[0]
                    delta = getattr(first_choice, "delta", None) or (first_choice.get("delta") if isinstance(first_choice, dict) else None)
                    if not delta:
                        continue
                    content = getattr(delta, "content", None) or (delta.get("content") if isinstance(delta, dict) else None)
                    if content:
                        if attempt > 0 and not model_ready_notified:
                            if status_manager:
                                status_manager.clear("llm")
                            if status_callback:
                                status_callback("✔ Model ready.")
                            else:
                                yield "[green]✔ Model ready.[/green]\n"
                            model_ready_notified = True
                        yield content
                if status_manager:
                    status_manager.clear("llm")
                if status_callback and model_ready_notified:
                    status_callback(None)
                break
            except AuthenticationError as e:
                if status_manager:
                    status_manager.clear("llm")
                if status_callback:
                    status_callback(None)
                yield f"[Authentication Error ({state.provider}): Please check your API key. Details: {e}]"
                return
            except RateLimitError as e:
                if status_manager:
                    status_manager.clear("llm")
                if status_callback:
                    status_callback(None)
                yield f"[Rate Limit Exceeded ({state.provider}): {e}]"
                return
            except (ServiceUnavailableError, APIConnectionError, APIError) as e:
                if is_cold_start_error(e):
                    attempt += 1
                    if attempt > max_attempts:
                        err_msg = f"LLM could not be started after {max_attempts} attempts."
                        if status_manager:
                            status_manager.clear("llm")
                        if status_callback:
                            status_callback(None)
                        yield f"[LLM Error ({state.provider}): {err_msg}]\n"
                        return

                    current_delay = initial_delay * (2 ** (attempt - 1))
                    status_text = (
                        f"LLM Cold Start: attempt {attempt}/{max_attempts} ({int(current_delay)}s) [Esc to cancel]"
                    )

                    if status_manager:
                        status_manager.set("llm", status_text)
                    if status_callback:
                        status_callback(status_text)
                    if not status_manager and not status_callback:
                        yield f"[yellow]⟳ {status_text}[/yellow]\n"

                    if cancel_event is not None:
                        try:
                            await asyncio.wait_for(cancel_event.wait(), timeout=current_delay)
                            if status_manager:
                                status_manager.clear("llm")
                            if status_callback:
                                status_callback(None)
                            yield "[yellow]LLM startup aborted.[/yellow]\n"
                            return
                        except asyncio.TimeoutError:
                            pass
                    else:
                        await asyncio.sleep(current_delay)
                else:
                    if status_manager:
                        status_manager.clear("llm")
                    if status_callback:
                        status_callback(None)
                    if isinstance(e, (APIConnectionError, ServiceUnavailableError)):
                        yield f"[Connection Error ({state.provider}): Unable to reach server. {e}]"
                    else:
                        yield f"[LLM Error ({state.provider}): {e}]"
                    return
            except Exception as e:
                if status_manager:
                    status_manager.clear("llm")
                if status_callback:
                    status_callback(None)
                yield f"[Unexpected Error ({state.provider}): {type(e).__name__} - {e}]"
                return

        if not chunks:
            break

        # Reconstruct response message to inspect tool calls
        try:
            stream_response_obj = stream_chunk_builder(chunks)
            response_msg = stream_response_obj.choices[0].message
        except Exception:
            break

        tool_calls = getattr(response_msg, "tool_calls", None)
        if not tool_calls:
            content_text = getattr(response_msg, "content", None)
            if content_text:
                if memory_obj is not None:
                    last_msg = memory_obj.messages[-1] if memory_obj.messages else None
                    last_role = last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", None)
                    if last_role != "assistant":
                        memory_obj.add_assistant(content_text)
                else:
                    last_msg = msg_list[-1] if msg_list else None
                    last_role = last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", None)
                    if last_role != "assistant":
                        msg_list.append({"role": "assistant", "content": content_text})
            break

        # Save assistant message with tool calls as a clean dictionary
        if hasattr(response_msg, "model_dump"):
            response_msg_dict = response_msg.model_dump(exclude_none=True)
        elif hasattr(response_msg, "dict"):
            response_msg_dict = response_msg.dict(exclude_none=True)
        elif isinstance(response_msg, dict):
            response_msg_dict = response_msg
        else:
            response_msg_dict = {"role": "assistant"}

        if isinstance(response_msg_dict, dict):
            response_msg_dict["role"] = "assistant"

        if memory_obj is not None:
            memory_obj.add_message(response_msg_dict)
        else:
            msg_list.append(response_msg_dict)

        # Execute tool calls
        for tool_call in tool_calls:
            func = getattr(tool_call, "function", None)
            func_name = getattr(func, "name", "unknown") if func else "unknown"
            func_args = getattr(func, "arguments", "") if func else ""
            tool_call_id = getattr(tool_call, "id", "") or f"call_{func_name}"

            display_str = format_tool_call_display(func_name, func_args)
            yield f"{display_str}\n"

            if status_manager:
                status_manager.set("tool", f"Execute tool: {func_name}...")
            try:
                tool_result = await run_tool(tool_call)
            finally:
                if status_manager:
                    status_manager.clear("tool")

            tool_msg = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_result,
            }
            if memory_obj is not None:
                memory_obj.add_message(tool_msg)
            else:
                msg_list.append(tool_msg)
