import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import docker
from docker.errors import DockerException

from .base_runner import BashRunner

class DockerSandbox(BashRunner):
    """
    Isolierte Docker-Ausführungsumgebung für Bash-Kommandos eines Coding-Agenten.

    Features:
    - User/Group-Mapping (keine root-Dateien auf dem Host)
    - Output-Truncation zum Schutz des LLM-Kontextfensters
    - Timeout-Absicherung gegen Endlosschleifen
    - Asynchrone und synchrone Aufruf-Schnittstellen
    """

    def __init__(
        self,
        workspace_path: Path,
        image: str = "python:3.11-slim",
        network_enabled: bool = False,
        memory_limit: str = "2g",
        max_output_chars: int = 12000,
    ):
        super().__init__(workspace_path, max_output_chars)
        self.image = image
        self.network_enabled = network_enabled
        self.memory_limit = memory_limit

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
                network_mode="bridge" if self.network_enabled else "none",
                mem_limit=self.memory_limit,
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

        # 'set -o pipefail' erkennt Fehler auch innerhalb von Pipes
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

        # Token-Schutz: Kürzen, falls Output zu lang wird
        if len(output_text) > self.max_output_chars:
            omitted = len(output_text) - self.max_output_chars
            output_text = (
                output_text[: self.max_output_chars]
                + f"\n\n[... {omitted} Zeichen gekürzt / Output Truncated ...]"
            )

        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "output": output_text or "(Keine Ausgabe)",
        }

    async def execute_async(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Führt ein Bash-Kommando asynchron mit Timeout aus."""
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

    async def execute(self, command: str, timeout: int = 30) -> str:
        """
        Synchrone Schnittstelle für dein TOOLS-Dictionary.
        Gibt das Ergebnis direkt als formatierte JSON-Zeichenkette zurück.
        """
        if not self.container:
            self.start()

        try:
            # Nutzt asyncio.run, falls kein aktiver Loop blockiert,
            # oder führt synchron direkt aus:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Falls bereits ein Async-Loop läuft (z.B. in der TUI)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self._sync_exec, command)
                    result = future.result(timeout=timeout)
            else:
                result = self._sync_exec(command)

        except TimeoutError:
            result = {
                "success": False,
                "exit_code": 124,
                "output": f"Kommando-Timeout nach {timeout} Sekunden erreicht.",
            }
        except Exception as exc:
            result = {
                "success": False,
                "exit_code": -1,
                "output": f"Fehler: {str(exc)}",
            }

        return json.dumps(result, ensure_ascii=False)

    def stop(self) -> None:
        """Beendet und entfernt den Container sauber."""
        if self.container:
            try:
                self.container.kill()
            except Exception:
                pass
            self.container = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
