import cleankoda_cli.llm as llm_module
from cleankoda_cli.commands.registry import CommandContext, CommandResult, registry


@registry.register("model", description="View or switch the LLM model", usage="/model [model_name]")
def cmd_model(args: list[str], ctx: CommandContext) -> CommandResult:
    if not args:
        return CommandResult(output=f"Current model: {llm_module.model_name}")
    new_model = args[0]
    llm_module.model = new_model
    return CommandResult(output=f"Model switched to: {new_model}")
