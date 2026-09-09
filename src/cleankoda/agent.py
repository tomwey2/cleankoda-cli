import asyncio
import json
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

from litellm import stream_chunk_builder

from cleankoda.commands import CommandContext, registry
from cleankoda.llm import LLMService
from cleankoda.memory import Memory
from cleankoda.sandbox import SandboxManager
from cleankoda.session_state import SessionState, StatusManager
from cleankoda.tools import TOOL_SCHEMAS, run_tool, sandbox_manager

SYSTEM_PROMPT = """You are a coding agent running in the user's terminal.
You can list files, read files, write files, and run shell commands.
Use your tools to complete the user's task, then briefly summarize what you did.
The working directory is the folder the user launched you from."""


async def run_agent(
    memory: Memory,
    llm_service: LLMService,
    tools: list[dict[str, Any]],
    state: SessionState,
    status_manager: StatusManager | None = None,
    cancel_event: asyncio.Event | None = None,
    max_tool_iterations: int = 10,
) -> AsyncGenerator[str, None]:
    """Central agent loop orchestrator.
    Iteratively calls LLM service, streams responses, executes tools, and records assistant and tool messages in memory.
    """
    iteration = 0

    while iteration < max_tool_iterations:
        if cancel_event is not None and cancel_event.is_set():
            yield "[yellow]Agent execution cancelled.[/yellow]\n"
            return

        iteration += 1
        chunks: list[Any] = []

        async for chunk in llm_service.stream_completion(
            messages=memory,
            state=state,
            tools=tools,
            cancel_event=cancel_event,
            chunks_out=chunks,
        ):
            yield chunk

        if cancel_event is not None and cancel_event.is_set():
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
                last_msg = memory.messages[-1] if memory.messages else None
                last_role = last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", None)
                if last_role != "assistant":
                    memory.add_assistant(content_text)
            break

        # Save assistant message with tool calls as a clean dictionary in memory
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

        memory.add_message(response_msg_dict)

        # Execute tool calls
        for tool_call in tool_calls:
            if cancel_event is not None and cancel_event.is_set():
                yield "[yellow]Tool execution cancelled.[/yellow]\n"
                return

            func = getattr(tool_call, "function", None)
            func_name = getattr(func, "name", "unknown") if func else "unknown"
            func_args = getattr(func, "arguments", "") if func else ""
            tool_call_id = getattr(tool_call, "id", "") or f"call_{func_name}"

            display_str = llm_service.format_tool_call_display(func_name, func_args)
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
            memory.add_message(tool_msg)
