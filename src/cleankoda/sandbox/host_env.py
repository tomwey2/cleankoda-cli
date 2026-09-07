import asyncio
import os
from pathlib import Path
from typing import Any, Dict

from cleankoda.sandbox.base import ExecutionEnvironment


class HostSandbox(ExecutionEnvironment):
    """Null-Object Implementation: Executes commands directly on the host system in the workspace."""

    def __init__(
        self,
        workspace_path: Path,
        max_output_chars: int = 12000,
    ) -> None:
        super().__init__(workspace_path, max_output_chars)

    async def run(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Executes a command asynchronously as a subprocess on the host."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # stderr in stdout mergen
                executable="/bin/bash" if os.name != "nt" else None,
            )

            stdout_bytes, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=float(timeout),
            )
            exit_code = process.returncode or 0
            output_text = stdout_bytes.decode("utf-8", errors="replace").strip()
            output_text = self._truncate_output(output_text)

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": output_text or "(No output)",
            }

        except asyncio.TimeoutError:
            try:
                process.kill()
            except (ProcessLookupError, UnboundLocalError):
                pass
            return {
                "success": False,
                "exit_code": 124,
                "output": f"Command timeout reached after {timeout} seconds.",
            }
        except Exception as exc:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"Host execution error: {str(exc)}",
            }
