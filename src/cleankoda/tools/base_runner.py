from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class BashRunner(ABC):
    """Abstrakte Basisklasse für alle Shell-Ausführungsumgebungen."""

    def __init__(self, workspace_path: Path, max_output_chars: int = 12000):
        self.workspace_path = workspace_path.resolve()
        self.max_output_chars = max_output_chars

    def truncate_output(self, output: str) -> str:
        """Kürzt zu lange Ausgaben zum Schutz des Kontextfensters."""
        if len(output) > self.max_output_chars:
            omitted = len(output) - self.max_output_chars
            return (
                output[: self.max_output_chars]
                + f"\n\n[... {omitted} Zeichen gekürzt / Output Truncated ...]"
            )
        return output

    @abstractmethod
    async def execute_async(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Muss von Subklassen implementiert werden."""
        pass

    @abstractmethod
    async def execute(self, command: str, timeout: int = 30) -> str:
        """Gibt das Ergebnis formatiert als JSON-String zurück."""
        pass

    def start(self) -> None:
        """Optionaler Lifecycle-Hook (z. B. Container starten)."""
        pass

    def stop(self) -> None:
        """Optionaler Lifecycle-Hook (z. B. Container beenden)."""
        pass
