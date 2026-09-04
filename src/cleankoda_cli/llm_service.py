import logging
from typing import AsyncGenerator, Any

import litellm
from litellm import stream_chunk_builder
from litellm.exceptions import (
    APIError,
    AuthenticationError,
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
)

from cleankoda_cli.session_state import SessionState
from cleankoda_cli.tools import TOOL_SCHEMAS, run_tool

litellm.suppress_debug_info = True


async def stream_chat_response(
    messages: list[dict[str, Any]] | Any,
    state: SessionState,
    tools: list[dict[str, Any]] | None = TOOL_SCHEMAS,
) -> AsyncGenerator[str, None]:
    """Streamt Antworten von LiteLLM basierend auf dem angegebenen SessionState und führt ggf. Tool-Calls aus."""
    litellm.suppress_debug_info = True

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

        if tools:
            kwargs["tools"] = tools

        if api_key:
            kwargs["api_key"] = api_key

        chunks = []
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
                    yield content

        except AuthenticationError as e:
            yield f"[Authentication Error ({state.provider}): Please check your API key. Details: {e}]"
            return
        except RateLimitError as e:
            yield f"[Rate Limit Exceeded ({state.provider}): {e}]"
            return
        except (APIConnectionError, ServiceUnavailableError) as e:
            yield f"[Connection Error ({state.provider}): Unable to reach server. {e}]"
            return
        except APIError as e:
            yield f"[LLM Error ({state.provider}): {e}]"
            return
        except Exception as e:
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

            yield f"\n[Tool Execution: {func_name}({func_args})]\n"

            tool_result = run_tool(tool_call)

            yield f"[Tool Output]: {tool_result}\n"

            tool_msg = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_result,
            }
            if memory_obj is not None:
                memory_obj.add_message(tool_msg)
            else:
                msg_list.append(tool_msg)
