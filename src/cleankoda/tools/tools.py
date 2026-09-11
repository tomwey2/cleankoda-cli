import json
from typing import Any, Callable

from cleankoda.sandbox import Sandbox
from cleankoda.tools.bash import BashCommand
from cleankoda.tools.filesystem import JailedFilesystem
from cleankoda.tools.schemas import TOOL_SCHEMAS


class Tools:
    """Manages agent tools (filesystem & bash) and tool execution."""

    def __init__(self, sandbox: Sandbox) -> None:
        self.sandbox = sandbox
        self.fs = JailedFilesystem(workspace_root=sandbox.workspace)
        self.bash_tool = BashCommand(sandbox=sandbox)
        self.schemas = TOOL_SCHEMAS
        self._tools: dict[str, Callable[..., Any]] = {
            "read_file": self.fs.read_file,
            "write_file": self.fs.write_file,
            "list_dir": self.fs.list_dir,
            "run_bash": self.bash_tool.execute,
        }

    def get_schemas(self) -> list[dict[str, Any]]:
        """Returns schemas of all registered tools."""
        return self.schemas

    async def run_tool(self, tool_call: Any) -> str:
        """Executes a tool call using the tools managed by this registry."""
        func = getattr(tool_call, "function", None)
        if func:
            name = getattr(func, "name", None) or (func.get("name") if isinstance(func, dict) else None)
            args_str = getattr(func, "arguments", "{}") or (func.get("arguments") if isinstance(func, dict) else "{}")
        elif isinstance(tool_call, dict):
            fn_dict = tool_call.get("function", {})
            name = fn_dict.get("name")
            args_str = fn_dict.get("arguments", "{}")
        else:
            name = None
            args_str = "{}"

        if isinstance(args_str, str):
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}
        else:
            args = args_str or {}

        if not name or name not in self._tools:
            return f"Error: Tool '{name}' not found."

        try:
            return await self._tools[name](**args)
        except Exception as error:
            return f"Error: {error}"
