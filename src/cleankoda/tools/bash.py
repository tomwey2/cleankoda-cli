import json
from cleankoda.sandbox.manager import SandboxManager


class BashCommand:
    """Agenten-Tool zum Ausführen von Shell-Befehlen über einen SandboxManager."""

    def __init__(self, sandbox_manager: SandboxManager) -> None:
        self.sandbox_manager = sandbox_manager

    async def execute(self, command: str, timeout: int = 30) -> str:
        """Führt ein Kommando in der aktiven Umgebung aus und liefert ein JSON-Ergebnis."""
        result = await self.sandbox_manager.current_env.run(command=command, timeout=timeout)
        return json.dumps(result, ensure_ascii=False)
