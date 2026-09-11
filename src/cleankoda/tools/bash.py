import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cleankoda.sandbox.sandbox import Sandbox


class BashCommand:
    """Agent tool for running shell commands in a sandbox environment."""

    def __init__(self, sandbox: "Sandbox") -> None:
        self.sandbox = sandbox

    async def execute(self, command: str, timeout: int = 30) -> str:
        """Executes a command in the active environment and returns a JSON result."""
        result = await self.sandbox.current_env.run(command=command, timeout=timeout)
        return json.dumps(result, ensure_ascii=False)
