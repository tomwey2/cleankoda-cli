import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict


from .base_runner import BashRunner


class HostRunner(BashRunner):
    """Führt Bash-Befehle direkt auf dem Host-System im Workspace aus."""

    def __init__(self, workspace_path: Path, max_output_chars: int = 12000):
        super().__init__(workspace_path, max_output_chars)

    async def execute_async(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Führt ein Kommando asynchron als Subprozess auf dem Host aus."""
        try:
            # Subprozess starten, gebunden an das Workspace-Verzeichnis
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # stderr in stdout mergen
                executable="/bin/bash" if os.name != "nt" else None,
            )

            # Timeout-Handling
            stdout_bytes, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=float(timeout),
            )
            exit_code = process.returncode or 0
            output_text = stdout_bytes.decode("utf-8", errors="replace").strip()

        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            return {
                "success": False,
                "exit_code": 124,
                "output": f"Kommando-Timeout nach {timeout} Sekunden erreicht.",
            }
        except Exception as exc:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"Host-Ausführungsfehler: {str(exc)}",
            }

        # Token-Schutz
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

    async def execute(self, command: str, timeout: int = 30) -> str:
        """Schnittstelle für das TOOLS-Dictionary (liefert serialisiertes JSON)."""
        result = await self.execute_async(command, timeout)
        return json.dumps(result, ensure_ascii=False)
