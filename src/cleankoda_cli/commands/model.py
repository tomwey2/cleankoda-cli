import asyncio
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.widgets import Button, Dialog, RadioList

from cleankoda_cli.commands.registry import CommandContext, CommandResult, registry
from cleankoda_cli.config import get_model, get_models_for_provider, get_provider, set_model


async def _show_tui_modal_model_dialog(
    app: Application,
    float_container: FloatContainer,
    models: list[str],
    provider_name: str,
    default_model: str | None = None,
) -> str | None:
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    values = [(m, m) for m in models]
    radio_list = RadioList(
        values=values,
        default=default_model if default_model in models else models[0],
    )

    def on_ok() -> None:
        if not fut.done():
            fut.set_result(radio_list.current_value)

    def on_cancel() -> None:
        if not fut.done():
            fut.set_result(None)

    modal_kb = KeyBindings()

    @modal_kb.add("escape", eager=True)
    def _cancel(event):
        on_cancel()

    @modal_kb.add("enter")
    def _select(event):
        on_ok()

    dialog = Dialog(
        title=f"Select Model ({provider_name})",
        body=radio_list,
        buttons=[
            Button("OK", handler=on_ok),
            Button("Cancel", handler=on_cancel),
        ],
        width=55,
        with_background=True,
    )

    dialog_container = HSplit([dialog], key_bindings=modal_kb)
    dialog_float = Float(content=dialog_container)

    float_container.floats.append(dialog_float)
    original_focused = app.layout.current_window
    app.layout.focus(radio_list)
    app.invalidate()

    try:
        result = await fut
    finally:
        if dialog_float in float_container.floats:
            float_container.floats.remove(dialog_float)
        if original_focused:
            app.layout.focus(original_focused)
        app.invalidate()

    return result


async def select_model_interactive(
    ctx: CommandContext | None = None, default_model: str | None = None
) -> str | None:
    """Zeigt einen interaktiven Dialog zur Auswahl des Modells (gefiltert nach aktuellem Provider, ESC bricht ab)."""
    active_provider = get_provider() or "mistral"
    available_models = get_models_for_provider(active_provider)

    app = ctx.app if ctx else None
    float_container = getattr(app, "float_container", None) if app else None

    if app and float_container:
        return await _show_tui_modal_model_dialog(
            app, float_container, available_models, active_provider, default_model
        )

    # Fallback für Headless / Non-TUI Modus
    values = [(m, m) for m in available_models]
    dialog = radiolist_dialog(
        title=f"Select Model ({active_provider})",
        text=f"Select an LLM model for provider '{active_provider}' (ESC to cancel):",
        values=values,
        default=default_model if default_model in available_models else available_models[0],
    )
    return dialog.run()


@registry.register(
    "model",
    description="View or switch the LLM model",
    usage="/model [model_name]",
)
async def cmd_model(args: list[str], ctx: CommandContext) -> CommandResult:
    """Slash-Command Handler für /model."""
    if args:
        new_model = args[0].strip()
        set_model(new_model)
        return CommandResult(output=f"Model switched to: {new_model}")

    current_model = get_model()
    selected_model = await select_model_interactive(ctx, current_model)

    if selected_model is None:
        return CommandResult(output="Model selection cancelled.")

    set_model(selected_model)
    return CommandResult(output=f"Model switched to: {selected_model}")
