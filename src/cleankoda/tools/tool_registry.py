from pathlib import Path
from typing import Any, Callable, Coroutine

from cleankoda.sandbox.config import DEFAULT_IMAGE
from cleankoda.sandbox.manager import SandboxManager
from cleankoda.tools.bash import BashCommand
from cleankoda.tools.filesystem import JailedFilesystem

# Instanzen für den aktuellen Projektordner
workspace = Path.cwd()
fs = JailedFilesystem(workspace_root=workspace)
sandbox_manager = SandboxManager(workspace_path=workspace, default_image=DEFAULT_IMAGE)
bash_tool = BashCommand(sandbox_manager=sandbox_manager)

# Das einheitliche, rein asynchrone Tool-Dictionary
AsyncToolCallable = Callable[..., Coroutine[Any, Any, str]]

# Das zentrale Tool-Registry-Dictionary
TOOLS: dict[str, Callable[..., Any]] = {
    # Host-Tools (Path-Jailed, extrem schnell)
    "read_file": fs.read_file,
    "write_file": fs.write_file,
    "list_dir": fs.list_dir,
    "run_bash": bash_tool.execute,
}

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


async def run_tool(tool_call: Any) -> str:
    """Führt einen Tool-Call aus und gibt das Ergebnis als String zurück."""
    import json

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

    if not name or name not in TOOLS:
        return f"Error: Tool '{name}' not found."

    try:
        result = await TOOLS[name](**args)
        return result
    except Exception as error:
        return f"Error: {error}"


def switch_runner(use_sandbox_param: bool, image: str | None = None) -> str:
    """Safely switch environment in sandbox_manager."""
    if use_sandbox_param and image and image != "host":
        return sandbox_manager.switch_environment(image)
    else:
        return sandbox_manager.switch_environment("host")


def get_sandbox_status() -> str:
    """Return active image name or 'host' for status line display."""
    return sandbox_manager.get_status()


def toggle_sandbox(enabled: bool) -> str:
    if enabled:
        current_status = get_sandbox_status()
        image = current_status if current_status != "host" else DEFAULT_IMAGE
        return switch_runner(True, image)
    else:
        return switch_runner(False)
