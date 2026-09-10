from cleankoda.commands.command_registry import CommandContext, CommandResult, registry


@registry.register("exit", description="Exit the application", aliases=["quit", "q"])
def cmd_exit(args: list[str], ctx: CommandContext) -> CommandResult:
    return CommandResult(output="Goodbye!", should_exit=True)
