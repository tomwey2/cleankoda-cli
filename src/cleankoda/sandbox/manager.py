from pathlib import Path

from cleankoda.sandbox.base import ExecutionEnvironment
from cleankoda.sandbox.config import DEFAULT_IMAGE
from cleankoda.sandbox.docker_env import DockerSandbox
from cleankoda.sandbox.host_env import HostSandbox


class SandboxManager:
    """Manages the lifecycle and switching of the execution environment."""

    def __init__(
        self,
        workspace_path: Path,
        default_image: str | None = DEFAULT_IMAGE,
    ) -> None:
        self.workspace_path = workspace_path.resolve()
        self.current_env: ExecutionEnvironment = HostSandbox(self.workspace_path)
        self.is_starting: bool = False
        if default_image and default_image != "host":
            # Prepare DockerSandbox (start asynchronously via start_async or run)
            self.current_env = DockerSandbox(self.workspace_path, image=default_image)

    async def switch_environment(self, image: str | None) -> str:
        """
        Stops the active environment and asynchronously switches to a new one.
        If `image` is specified (and != "host"), a DockerSandbox is started.
        If `None` or "host" is specified, the HostSandbox (Null Object Pattern) is used.
        """
        self.current_env.stop()

        if image and image != "host":
            self.is_starting = True
            try:
                new_env = DockerSandbox(self.workspace_path, image=image)
                await new_env.start_async()
                self.current_env = new_env
                return f"Sandbox enabled: Image [{image}]"
            except Exception as exc:
                self.current_env = HostSandbox(self.workspace_path)
                return f"Error starting sandbox ({exc}). Fallback to host system."
            finally:
                self.is_starting = False
        else:
            self.is_starting = False
            self.current_env = HostSandbox(self.workspace_path)
            return "Sandbox disabled: Commands run directly on the host."

    def get_status(self) -> str:
        """Returns the name of the active Docker image, 'Starting...' or 'host'."""
        if self.is_starting:
            return "Starting..."
        image = getattr(self.current_env, "image", None)
        return image if image else "host"

    def stop(self) -> None:
        """Cleanly shuts down the active execution environment."""
        self.current_env.stop()
