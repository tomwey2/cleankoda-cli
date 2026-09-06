from pathlib import Path
import subprocess
from typing import Any, Callable, Coroutine

from cleankoda.tools.filesystem import JailedFilesystem
from cleankoda.tools.sandbox import DockerSandbox
from cleankoda.tools.host_runner import HostRunner

# Instanzen für den aktuellen Projektordner
workspace = Path.cwd()
fs = JailedFilesystem(workspace_root=workspace)
sandbox = DockerSandbox(workspace_path=workspace)
host_runner = HostRunner(workspace_path=workspace)
use_sandbox = True

async def dispatch_bash(command: str, timeout: int = 30) -> str:
    """
    Dynamischer Dispatcher für Shell-Befehle:
    Leitet das Kommando je nach aktuellem Flag an die Docker-Sandbox
    oder den Host-Runner weiter. Beide Schnittstellen sind asynchron.
    """
    runner = sandbox if use_sandbox else host_runner
    return await runner.execute(command=command, timeout=timeout)

# Das einheitliche, rein asynchrone Tool-Dictionary
AsyncToolCallable = Callable[..., Coroutine[Any, Any, str]]

# Das zentrale Tool-Registry-Dictionary
TOOLS: dict[str, Callable[..., Any]] = {
    # Host-Tools (Path-Jailed, extrem schnell)
    "read_file": fs.read_file,
    "write_file": fs.write_file,
    "list_dir": fs.list_dir,
    "run_bash": dispatch_bash,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function":{
            "name": "list_dir",
            "description": "List the files in a directory. Folders end with /.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": { "type": "string", "description": "Directory to list, e.g. '.'"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function":{
            "name": "read_file",
            "description": "Read a text file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": { "type": "string", "description": "Path of the file to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function":{
            "name": "write_file",
            "description": "Create or overwrite a text file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": { "type": "string", "description": "Path of the file to write"},
                    "content": { "type": "string", "description": "Full contents of the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function":{
            "name": "run_bash",
            "description": "Run a shell command and return its output. The user approves it first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": { "type": "string", "description": "The shell command to run"},
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


def toggle_sandbox(enabled: bool) -> str:
    global use_sandbox
    use_sandbox = enabled
    if enabled and not sandbox.container:
        sandbox.start()
    return f"Sandbox ist nun {'aktiviert' if enabled else 'deaktiviert'}."
