import json
from pathlib import Path
from typing import Any, Callable, Coroutine

from cleankoda.sandbox.config import DEFAULT_IMAGE
from cleankoda.sandbox.manager import SandboxManager
from cleankoda.tools.bash import BashCommand
from cleankoda.tools.filesystem import JailedFilesystem

AsyncToolCallable = Callable[..., Coroutine[Any, Any, str]]

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the files in a directory. Folders end with /.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to list, e.g. '.'"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to write"},
                    "content": {"type": "string", "description": "Full contents of the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command and return its output. The user approves it first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"},
                },
                "required": ["command"],
            },
        },
    },
]


class ToolRegistry:
    """Manages filesystems, sandboxes, tools, schemas, and execution for a specific workspace."""

    def __init__(
        self,
        workspace: Path,
        sandbox_image: str | None = DEFAULT_IMAGE,
    ) -> None:
        self.workspace = workspace.resolve()
        self.fs = JailedFilesystem(workspace_root=self.workspace)
        self.sandbox_manager = SandboxManager(
            workspace_path=self.workspace,
            default_image=sandbox_image,
        )
        self.bash_tool = BashCommand(sandbox_manager=self.sandbox_manager)

        self._tools: dict[str, Callable[..., Any]] = {
            "read_file": self.fs.read_file,
            "write_file": self.fs.write_file,
            "list_dir": self.fs.list_dir,
            "run_bash": self.bash_tool.execute,
        }
        self.schemas = TOOL_SCHEMAS

    async def run_tool(self, tool_call: Any) -> str:
        """Executes a tool call using the instances managed by this registry."""
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

    async def switch_runner(self, use_sandbox_param: bool, image: str | None = None) -> str:
        """Safely switch environment in sandbox_manager."""
        if use_sandbox_param and image and image != "host":
            return await self.sandbox_manager.switch_environment(image)
        else:
            return await self.sandbox_manager.switch_environment("host")

    def get_sandbox_status(self) -> str:
        """Return active image name, 'Starting...' or 'host' for status line display."""
        return self.sandbox_manager.get_status()

    async def toggle_sandbox(self, enabled: bool) -> str:
        """Toggle sandbox execution environment on or off."""
        if enabled:
            current_status = self.get_sandbox_status()
            image = current_status if current_status not in ("host", "Starting...") else DEFAULT_IMAGE
            return await self.switch_runner(True, image)
        else:
            return await self.switch_runner(False)

    def stop(self) -> None:
        """Stops the underlying sandbox execution environment."""
        self.sandbox_manager.stop()
