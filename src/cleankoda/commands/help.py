from cleankoda.commands.command_registry import CommandContext, CommandResult, registry


@registry.register("help", description="List all available commands")
def cmd_help(args: list[str], ctx: CommandContext) -> CommandResult:
    cmds = registry.list_commands()
    lines = ["Available Commands:"]
    for c in cmds:
        aliases_str = f" (aliases: {', '.join('/' + a for a in c.aliases)})" if c.aliases else ""
        lines.append(f"  /{c.name:<10} - {c.description}{aliases_str}")
    return CommandResult(output="\n".join(lines))
