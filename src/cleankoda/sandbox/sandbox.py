import json
from pathlib import Path
from typing import Any, Callable

from cleankoda.sandbox.base_env import ExecutionEnvironment
from cleankoda.sandbox.config import DEFAULT_IMAGE
from cleankoda.sandbox.docker_env import DockerEnvironment
from cleankoda.sandbox.host_env import HostEnvironment
from cleankoda.statusline import statusline
from cleankoda.tools.bash import BashCommand
from cleankoda.tools.filesystem import JailedFilesystem
from cleankoda.tools.schemas import TOOL_SCHEMAS


class Sandbox:
    """Manages workspace execution environment lifecycle (host/docker) and tools."""

    def __init__(
        self,
        workspace: Path,
        default_image: str | None = DEFAULT_IMAGE,
    ) -> None:
        self.workspace = workspace.resolve()
        self.workspace_path = self.workspace
        self.is_starting: bool = False

        self.current_env: ExecutionEnvironment = HostEnvironment(self.workspace)
        if default_image and default_image != "host":
            self.current_env = DockerEnvironment(self.workspace, image=default_image)

        self.fs = JailedFilesystem(workspace_root=self.workspace)
        self.bash_tool = BashCommand(sandbox=self)

        self._tools: dict[str, Callable[..., Any]] = {
            "read_file": self.fs.read_file,
            "write_file": self.fs.write_file,
            "list_dir": self.fs.list_dir,
            "run_bash": self.bash_tool.execute,
        }
        self.schemas = TOOL_SCHEMAS

    async def switch_environment(self, image: str | None) -> str:
        """Stops the active environment and asynchronously switches to host or docker image."""
        self.current_env.stop()

        if image and image != "host":
            self.is_starting = True
            statusline.set("sandbox", f"Sandbox: starting ({image})...")
            try:
                new_env = DockerEnvironment(self.workspace, image=image)
                await new_env.start_async()
                self.current_env = new_env
                return f"Sandbox enabled: Image [{image}]"
            except Exception as exc:
                self.current_env = HostEnvironment(self.workspace)
                return f"Error starting sandbox ({exc}). Fallback to host system."
            finally:
                self.is_starting = False
                statusline.clear("sandbox")
        else:
            self.is_starting = False
            statusline.clear("sandbox")
            self.current_env = HostEnvironment(self.workspace)
            return "Sandbox disabled: Commands run directly on the host."

    async def switch_runner(self, use_sandbox_param: bool, image: str | None = None) -> str:
        """Safely switch environment in sandbox."""
        if use_sandbox_param and image and image != "host":
            return await self.switch_environment(image)
        else:
            return await self.switch_environment("host")

    def get_status(self) -> str:
        """Returns the name of the active Docker image, 'Starting...' or 'host'."""
        if self.is_starting:
            return "Starting..."
        image = getattr(self.current_env, "image", None)
        return image if image else "host"

    def get_sandbox_status(self) -> str:
        """Alias for get_status."""
        return self.get_status()

    async def toggle_sandbox(self, enabled: bool) -> str:
        """Toggles sandbox execution environment on or off."""
        if enabled:
            current_status = self.get_status()
            image = current_status if current_status not in ("host", "Starting...") else DEFAULT_IMAGE
            return await self.switch_runner(True, image)
        else:
            return await self.switch_runner(False)

    def stop(self) -> None:
        """Cleanly shuts down active execution environment."""
        self.current_env.stop()

    async def run_tool(self, tool_call: Any) -> str:
        """Executes a tool call using the tools managed by this sandbox."""
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
