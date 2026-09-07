from pathlib import Path

from cleankoda.sandbox.base import ExecutionEnvironment
from cleankoda.sandbox.config import DEFAULT_IMAGE
from cleankoda.sandbox.docker_env import DockerSandbox
from cleankoda.sandbox.host_env import HostSandbox


class SandboxManager:
    """Verwaltet den Lifecycle und das Umschalten der Ausführungsumgebung."""

    def __init__(
        self,
        workspace_path: Path,
        default_image: str | None = DEFAULT_IMAGE,
    ) -> None:
        self.workspace_path = workspace_path.resolve()
        self.current_env: ExecutionEnvironment = HostSandbox(self.workspace_path)
        if default_image and default_image != "host":
            self.switch_environment(default_image)

    def switch_environment(self, image: str | None) -> str:
        """
        Stoppt die aktive Umgebung und schaltet auf eine neue Umgebung um.
        Wenn `image` angegeben ist (und != "host"), wird eine DockerSandbox erstellt.
        Bei `None` oder "host" wird die HostSandbox (Null Object Pattern) verwendet.
        """
        self.current_env.stop()

        if image and image != "host":
            try:
                new_env = DockerSandbox(self.workspace_path, image=image)
                new_env.start()
                self.current_env = new_env
                return f"Sandbox aktiv: Image [{image}]"
            except Exception as exc:
                self.current_env = HostSandbox(self.workspace_path)
                return f"Fehler beim Starten der Sandbox ({exc}). Fallback auf Host-System."
        else:
            self.current_env = HostSandbox(self.workspace_path)
            return "Sandbox deaktiviert: Befehle laufen direkt auf dem Host."

    def get_status(self) -> str:
        """Gibt den Namen des aktiven Docker-Images oder 'host' zurück."""
        image = getattr(self.current_env, "image", None)
        return image if image else "host"

    def stop(self) -> None:
        """Fährt die aktive Ausführungsumgebung sauber herunter."""
        self.current_env.stop()
