from cleankoda.commands.registry import CommandContext, CommandResult, registry
from cleankoda.config import CONFIG_FILE
from cleankoda.session_state import SessionState


@registry.register(
    "temp",
    description="View or set the LLM temperature (e.g. 0.2)",
    usage="/temp [value]",
)
async def cmd_temp(args: list[str], ctx: CommandContext) -> CommandResult:
    """Slash-Command Handler für /temp."""
    state = SessionState.load(file_path=CONFIG_FILE)

    if not args:
        return CommandResult(output=f"Current temperature: {state.temperature}")

    try:
        val = float(args[0].strip())
        if not (0.0 <= val <= 2.0):
            return CommandResult(output="Temperature must be between 0.0 and 2.0.")
        state.temperature = val
        state.save(file_path=CONFIG_FILE)
        return CommandResult(output=f"Temperature set to: {val}")
    except ValueError:
        return CommandResult(output=f"Invalid temperature value '{args[0]}'. Please provide a number (e.g. 0.7).")
