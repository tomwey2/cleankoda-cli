from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CommandContext:
    """Context passed to command execution handlers."""

    memory: Any
    app: Any | None = None
    state: dict | None = None


@dataclass
class CommandResult:
    """Result returned by a command handler execution."""

    output: str | None = None
    should_exit: bool = False


CommandHandler = Callable[[list[str], CommandContext], CommandResult]


@dataclass
class Command:
    name: str
    description: str
    usage: str
    handler: CommandHandler
    aliases: list[str]


class CommandRegistry:
    """Registry managing registration and execution of slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(
        self,
        name: str,
        description: str,
        usage: str = "",
        aliases: list[str] | None = None,
    ):
        """Decorator to register a command handler function."""
        if aliases is None:
            aliases = []

        def decorator(func: CommandHandler) -> CommandHandler:
            cmd_name = name.lstrip("/")
            cmd = Command(
                name=cmd_name,
                description=description,
                usage=usage or f"/{cmd_name}",
                handler=func,
                aliases=[a.lstrip("/") for a in aliases],
            )
            self._commands[cmd_name] = cmd
            for alias in cmd.aliases:
                self._commands[alias] = cmd
            return func

        return decorator

    def dispatch(self, user_input: str, ctx: CommandContext) -> CommandResult:
        """Parse input line and execute matching command if found."""
        parts = user_input.strip().split()
        if not parts:
            return CommandResult()

        cmd_name = parts[0].lstrip("/").lower()
        args = parts[1:]

        if cmd_name not in self._commands:
            return CommandResult(
                output=f"Unknown command: '/{cmd_name}'. Type '/help' for available commands."
            )

        cmd = self._commands[cmd_name]
        try:
            return cmd.handler(args, ctx)
        except Exception as e:
            return CommandResult(output=f"Error executing '/{cmd_name}': {e}")

    def list_commands(self) -> list[Command]:
        """Return unique registered commands."""
        seen = set()
        unique_cmds = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                unique_cmds.append(cmd)
        return unique_cmds


registry = CommandRegistry()
