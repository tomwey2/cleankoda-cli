from pathlib import Path
import subprocess
from typing import Any, Callable, Coroutine

from cleankoda.tools.filesystem import JailedFilesystem
from cleankoda.tools.sandbox import DockerSandbox
from cleankoda.tools.host_runner import HostRunner

# Instanzen für den aktuellen Projektordner
workspace = Path.cwd()
fs = JailedFilesystem(workspace_root=workspace)
host_runner = HostRunner(workspace_path=workspace)
sandbox = DockerSandbox(workspace_path=workspace, image="python:3.11-slim")
active_runner = sandbox
use_sandbox = True
active_image = "python:3.11-slim"

async def dispatch_bash(command: str, timeout: int = 30) -> str:
    """
    Dynamischer Dispatcher für Shell-Befehle:
    Leitet das Kommando an den aktuell aktiven Runner (Docker-Sandbox oder Host-Runner) weiter.
    """
    return await active_runner.execute(command=command, timeout=timeout)

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


def switch_runner(use_sandbox_param: bool, image: str | None = None) -> str:
    """
    Safely stop current runner and switch to Docker Sandbox or HostRunner.
    Returns status message or error detail.
    """
    global active_runner, use_sandbox, active_image, sandbox

    if hasattr(active_runner, "stop"):
        try:
            active_runner.stop()
        except Exception:
            pass

    if use_sandbox_param and image and image != "host":
        try:
            new_sandbox = DockerSandbox(workspace_path=workspace, image=image)
            new_sandbox.start()
            sandbox = new_sandbox
            active_runner = sandbox
            use_sandbox = True
            active_image = image
            return f"Sandbox aktiv: Image [{image}]"
        except Exception as exc:
            active_runner = host_runner
            use_sandbox = False
            active_image = "host"
            return f"Fehler beim Starten der Sandbox ({exc}). Fallback auf Host-System."
    else:
        active_runner = host_runner
        use_sandbox = False
        active_image = "host"
        return "Sandbox deaktiviert: Befehle laufen direkt auf dem Host."


def get_sandbox_status() -> str:
    """Return active image name or 'host' for status line display."""
    if use_sandbox and active_image:
        return active_image
    return "host"


def toggle_sandbox(enabled: bool) -> str:
    if enabled:
        return switch_runner(True, active_image or "python:3.11-slim")
    else:
        return switch_runner(False)

