from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ExecutionEnvironment(ABC):
    """Abstract base class for execution environments (host & sandbox)."""

    def __init__(self, workspace_path: Path, max_output_chars: int = 12000) -> None:
        self.workspace_path = workspace_path.resolve()
        self.max_output_chars = max_output_chars

    def _truncate_output(self, text: str) -> str:
        """Shortens excessively long output to protect the LLM context window."""
        if len(text) > self.max_output_chars:
            omitted = len(text) - self.max_output_chars
            return (
                text[: self.max_output_chars]
                + f"\n\n[... {omitted} Zeichen gekürzt / Output Truncated ...]"
            )
        return text

    @abstractmethod
    async def run(self, command: str, timeout: int = 30) -> dict[str, Any]:
        """
        Executes a Bash command.
        Returns a dictionary containing {"success": bool, "exit_code": int, "output": str}.
        """
        pass

    def start(self) -> None:
        """Optional hook for starting resources (e.g., Docker containers)."""
        pass

    def stop(self) -> None:
        """Optional hook for releasing resources."""
        pass
