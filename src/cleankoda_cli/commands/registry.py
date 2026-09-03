import asyncio
import inspect
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


CommandHandler = Callable[[list[str], CommandContext], Any]


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

    def _get_command_and_args(
        self, user_input: str
    ) -> tuple[Command | None, list[str], CommandResult | None]:
        parts = user_input.strip().split()
        if not parts:
            return None, [], CommandResult()

        cmd_name = parts[0].lstrip("/").lower()
        args = parts[1:]

        if cmd_name not in self._commands:
            return (
                None,
                [],
                CommandResult(
                    output=f"Unknown command: '/{cmd_name}'. Type '/help' for available commands."
                ),
            )

        return self._commands[cmd_name], args, None

    def dispatch(self, user_input: str, ctx: CommandContext) -> CommandResult:
        """Parse input line and execute matching command if found (for sync contexts)."""
        cmd, args, err_res = self._get_command_and_args(user_input)
        if err_res is not None:
            return err_res

        assert cmd is not None
        try:
            res = cmd.handler(args, ctx)
            if inspect.isawaitable(res):
                return asyncio.run(res)
            return res
        except Exception as e:
            return CommandResult(output=f"Error executing '/{cmd.name}': {e}")

    async def dispatch_async(self, user_input: str, ctx: CommandContext) -> CommandResult:
        """Parse input line and execute matching command if found (for async contexts)."""
        cmd, args, err_res = self._get_command_and_args(user_input)
        if err_res is not None:
            return err_res

        assert cmd is not None
        try:
            res = cmd.handler(args, ctx)
            if inspect.isawaitable(res):
                return await res
            return res
        except Exception as e:
            return CommandResult(output=f"Error executing '/{cmd.name}': {e}")

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
