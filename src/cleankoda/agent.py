import json
import os
from pathlib import Path
from typing import Any
import litellm

from cleankoda.commands import CommandContext, registry
from cleankoda.memory import Memory
from cleankoda.sandbox import SandboxManager
from cleankoda.session_state import SessionState
from cleankoda.tools import TOOL_SCHEMAS, run_tool, sandbox_manager

SYSTEM_PROMPT = """You are a coding agent running in the user's terminal.
You can list files, read files, write files, and run shell commands.
Use your tools to complete the user's task, then briefly summarize what you did.
The working directory is the folder the user launched you from."""


def run_agent(memory: Memory, state: SessionState | None = None) -> str | None:
    if state is None:
        state = SessionState.load()

    litellm.suppress_debug_info = True
    model_identifier = state.litellm_model_identifier
    api_key = state.get_active_api_key()

    while True:
        kwargs: dict[str, Any] = {
            "model": model_identifier,
            "messages": memory.messages,
            "tools": TOOL_SCHEMAS,
            "temperature": state.temperature,
            "max_tokens": state.max_tokens,
        }
        if api_key:
            kwargs["api_key"] = api_key

        response = litellm.completion(**kwargs)
        message = response.choices[0].message
        memory.add_message(message)

        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            return message.content

        for tool_call in tool_calls:
            result = run_tool(tool_call)
            tool_call_id = getattr(tool_call, "id", None)
            if not tool_call_id and isinstance(tool_call, dict):
                tool_call_id = tool_call.get("id")
            memory.add_tool_message(tool_call_id=tool_call_id or "", content=result)
