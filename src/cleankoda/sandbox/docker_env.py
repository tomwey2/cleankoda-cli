import asyncio
import os
from pathlib import Path
from typing import Any, Dict

import docker
from docker.errors import DockerException

from cleankoda.sandbox.base import ExecutionEnvironment


class DockerSandbox(ExecutionEnvironment):
    """Isolierte Docker-Ausführungsumgebung für Shell-Befehle."""

    def __init__(
        self,
        workspace_path: Path,
        image: str = "python:3.11-slim",
        max_output_chars: int = 12000,
    ) -> None:
        super().__init__(workspace_path, max_output_chars)
        self.image = image
        self.client = docker.from_env()
        self.container = None

    def start(self) -> None:
        """Startet den Workspace-Container im Hintergrund."""
        if self.container is not None:
            return

        uid = os.getuid()
        gid = os.getgid()

        try:
            self.container = self.client.containers.run(
                image=self.image,
                command="tail -f /dev/null",  # Hält den Container am Leben
                detach=True,
                volumes={
                    str(self.workspace_path): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                working_dir="/workspace",
                user=f"{uid}:{gid}",
                network_mode="none",
                mem_limit="2g",
                nano_cpus=2 * 10**9,  # Max 2 CPUs
                remove=True,  # Container wird beim Stoppen automatisch gelöscht
            )
        except DockerException as exc:
            raise RuntimeError(f"Fehler beim Starten der Docker-Sandbox: {exc}") from exc

    def _sync_exec(self, command: str) -> Dict[str, Any]:
        """Blockierender exec-Call über das Docker Python SDK."""
        if not self.container:
            return {
                "success": False,
                "exit_code": -1,
                "output": "Error: Sandbox-Container läuft nicht.",
            }

        wrapped_cmd = f"bash -c 'set -o pipefail; {command}'"

        exec_instance = self.client.api.exec_create(
            self.container.id,
            cmd=wrapped_cmd,
            workdir="/workspace",
            environment={"TERM": "dumb"},  # Deaktiviert ANSI-Steuercodes
        )

        raw_output = self.client.api.exec_start(exec_instance)
        inspect_data = self.client.api.exec_inspect(exec_instance["Id"])
        exit_code = inspect_data.get("ExitCode", 0)

        output_text = raw_output.decode("utf-8", errors="replace").strip()
        output_text = self._truncate_output(output_text)

        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "output": output_text or "(Keine Ausgabe)",
        }

    async def run(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Führt ein Bash-Kommando asynchron mit Timeout in der Docker-Sandbox aus."""
        if not self.container:
            self.start()

        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._sync_exec, command),
                timeout=float(timeout),
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "exit_code": 124,
                "output": f"Kommando-Timeout nach {timeout} Sekunden erreicht.",
            }
        except Exception as exc:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"Ausführungsfehler: {str(exc)}",
            }

    def stop(self) -> None:
        """Beendet und entfernt den Container sauber."""
        if self.container:
            try:
                self.container.kill()
            except Exception:
                pass
            self.container = None
