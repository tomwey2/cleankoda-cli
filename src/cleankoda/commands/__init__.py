import importlib
import pkgutil
from cleankoda.commands.command_registry import CommandContext, CommandResult, registry


def _load_commands() -> None:
    """Dynamically import all command modules in the commands directory."""
    for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
        if not is_pkg and module_name != "registry":
            importlib.import_module(f"{__name__}.{module_name}")


_load_commands()

__all__ = ["registry", "CommandContext", "CommandResult"]
