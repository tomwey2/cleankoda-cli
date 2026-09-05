import importlib
import pkgutil
from cleankoda.commands.registry import CommandContext, CommandResult, registry


SLASH_COMMANDS: dict[str, str] = {
    "/plan": "Create a step-by-step implementation plan",
    "/provider": "Change the LLM provider and configure API keys",
    "/model": "Select the active model for the provider",
    "/clear": "Deletes the current chat history",
    "/help": "Displays all available commands",
    "/exit": "Ends the session",
    "/temp": "Displays or changes the LLM temperature (e.g., 0.2)",
}


def _load_commands() -> None:
    """Dynamically import all command modules in the commands directory."""
    for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
        if not is_pkg and module_name != "registry":
            importlib.import_module(f"{__name__}.{module_name}")


_load_commands()

__all__ = ["registry", "CommandContext", "CommandResult", "SLASH_COMMANDS"]
