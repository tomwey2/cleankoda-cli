from cleankoda_cli.commands.registry import CommandContext, CommandResult, registry


@registry.register("clear", description="Clear memory and conversation history")
def cmd_clear(args: list[str], ctx: CommandContext) -> CommandResult:
    if ctx.memory:
        ctx.memory.clear(keep_system=True)
    return CommandResult(output="Conversation memory cleared.")
