from cleankoda.commands.registry import CommandContext, CommandResult, registry
from cleankoda.config import config


@registry.register(
    "temp",
    description="View or set the LLM temperature (e.g. 0.2)",
    usage="/temp [value]",
)
async def cmd_temp(args: list[str], ctx: CommandContext) -> CommandResult:
    """Slash-Command Handler für /temp."""

    if not args:
        return CommandResult(output=f"Current temperature: {config.temperature}")

    try:
        val = float(args[0].strip())
        if not (0.0 <= val <= 2.0):
            return CommandResult(output="Temperature must be between 0.0 and 2.0.")
        config.temperature = val
        config.save()
        return CommandResult(output=f"Temperature set to: {config.temperature}")
    except ValueError:
        return CommandResult(output=f"Invalid temperature value '{args[0]}'. Please provide a number (e.g. 0.7).")
