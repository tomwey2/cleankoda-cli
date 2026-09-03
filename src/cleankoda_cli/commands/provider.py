import asyncio
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.widgets import Button, Dialog, RadioList

from cleankoda_cli.commands.registry import CommandContext, CommandResult, registry
from cleankoda_cli.config import PROVIDERS, get_provider, set_provider


async def _show_tui_modal_provider_dialog(
    app: Application, float_container: FloatContainer, default_provider: str | None = None
) -> str | None:
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    values = [(p, p) for p in PROVIDERS]
    radio_list = RadioList(
        values=values,
        default=default_provider if default_provider in PROVIDERS else PROVIDERS[0],
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
        title="Select Provider",
        body=radio_list,
        buttons=[
            Button("OK", handler=on_ok),
            Button("Cancel", handler=on_cancel),
        ],
        width=50,
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


async def select_provider_interactive(
    ctx: CommandContext | None = None, default_provider: str | None = None
) -> str | None:
    """Zeigt einen interaktiven Dialog zur Auswahl des Providers (ESC bricht ab)."""
    app = ctx.app if ctx else None
    float_container = getattr(app, "float_container", None) if app else None

    if app and float_container:
        return await _show_tui_modal_provider_dialog(app, float_container, default_provider)

    # Fallback für Headless / Non-TUI Modus
    values = [(p, p) for p in PROVIDERS]
    dialog = radiolist_dialog(
        title="Select Provider",
        text="Select an LLM provider (ESC to cancel):",
        values=values,
        default=default_provider if default_provider in PROVIDERS else PROVIDERS[0],
    )
    return dialog.run()


@registry.register(
    "provider",
    description="View or select the LLM provider",
    usage="/provider [provider_name]",
)
async def cmd_provider(args: list[str], ctx: CommandContext) -> CommandResult:
    """Slash-Command Handler für /provider."""
    if args:
        chosen_provider = args[0].strip().lower()
        if chosen_provider in PROVIDERS:
            set_provider(chosen_provider)
            return CommandResult(output=f"Provider switched to: {chosen_provider}")
        else:
            return CommandResult(
                output=f"Invalid provider '{args[0]}'. Available providers: {', '.join(PROVIDERS)}"
            )

    current_provider = get_provider()
    selected_provider = await select_provider_interactive(ctx, current_provider)

    if selected_provider is None:
        return CommandResult(output="Provider selection cancelled.")

    set_provider(selected_provider)
    return CommandResult(output=f"Provider switched to: {selected_provider}")
