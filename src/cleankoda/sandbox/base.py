from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class ExecutionEnvironment(ABC):
    """Abstrakte Basisklasse für Ausführungsumgebungen (Host & Sandbox)."""

    def __init__(self, workspace_path: Path, max_output_chars: int = 12000) -> None:
        self.workspace_path = workspace_path.resolve()
        self.max_output_chars = max_output_chars

    def _truncate_output(self, text: str) -> str:
        """Kürzt zu lange Ausgaben zum Schutz des LLM-Kontextfensters."""
        if len(text) > self.max_output_chars:
            omitted = len(text) - self.max_output_chars
            return (
                text[: self.max_output_chars]
                + f"\n\n[... {omitted} Zeichen gekürzt / Output Truncated ...]"
            )
        return text

    @abstractmethod
    async def run(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Führt ein Bash-Kommando aus.
        Liefert ein Dictionary mit {"success": bool, "exit_code": int, "output": str}.
        """
        pass

    def start(self) -> None:
        """Optionaler Hook zum Starten von Ressourcen (z. B. Docker Container)."""
        pass

    def stop(self) -> None:
        """Optionaler Hook zum Freigeben von Ressourcen."""
        pass
