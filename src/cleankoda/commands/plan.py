from cleankoda.commands.registry import CommandContext, CommandResult, registry


@registry.register(
    "plan",
    description="Erstellt einen schrittweisen Implementierungsplan",
    usage="/plan [goal]",
)
def cmd_plan(args: list[str], ctx: CommandContext) -> CommandResult:
    """Slash-Command Handler für /plan."""
    goal_text = " ".join(args).strip() if args else ""
    output_msg = (
        f"Planungsmodus gestartet für: '{goal_text}'"
        if goal_text
        else "Planungsmodus gestartet. Bitte beschreibe dein Ziel für den Implementierungsplan."
    )
    return CommandResult(output=output_msg)
