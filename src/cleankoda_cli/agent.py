import json
import os
from typing import Any
import litellm

from cleankoda_cli.commands import CommandContext, registry
from cleankoda_cli.session_state import SessionState
from cleankoda_cli.memory import Memory
from cleankoda_cli.tools import *

SYSTEM_PROMPT = """You are a coding agent running in the user's terminal.
You can list files, read files, write files, and run shell commands.
Use your tools to complete the user's task, then briefly summarize what you did.
The working directory is the folder the user launched you from."""


def run_tool(tool_call: Any) -> str:
    func = getattr(tool_call, "function", None)
    if func:
        name = func.name
        args_str = getattr(func, "arguments", "{}")
    else:
        name = tool_call.get("function", {}).get("name")
        args_str = tool_call.get("function", {}).get("arguments", "{}")

    if isinstance(args_str, str):
        args = json.loads(args_str)
    else:
        args = args_str

    try:
        return str(TOOLS[name](**args))
    except Exception as error:
        return f"Error: {error}"


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
