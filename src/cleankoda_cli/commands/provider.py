import asyncio
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.shortcuts import input_dialog, radiolist_dialog
from prompt_toolkit.widgets import Button, Dialog, RadioList, TextArea

from cleankoda_cli.commands.registry import CommandContext, CommandResult, registry
from cleankoda_cli.config import PROVIDERS, get_provider, set_provider
from cleankoda_cli.credentials import CredentialsStore


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


async def _show_tui_modal_api_key_dialog(
    app: Application,
    float_container: FloatContainer,
    provider_name: str,
    status_text: str,
) -> str | None:
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    input_field = TextArea(
        height=1,
        password=True,
        multiline=False,
        wrap_lines=False,
    )

    def on_ok() -> None:
        if not fut.done():
            fut.set_result(input_field.text)

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

    body = HSplit([
        Window(FormattedTextControl(status_text), height=2),
        input_field,
    ])

    dialog = Dialog(
        title=f"API-Key für {provider_name}",
        body=body,
        buttons=[
            Button("OK", handler=on_ok),
            Button("Cancel", handler=on_cancel),
        ],
        width=60,
        with_background=True,
    )

    dialog_container = HSplit([dialog], key_bindings=modal_kb)
    dialog_container.input_field = input_field
    dialog_float = Float(content=dialog_container)

    float_container.floats.append(dialog_float)
    original_focused = app.layout.current_window
    app.layout.focus(input_field)
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

    values = [(p, p) for p in PROVIDERS]
    dialog = radiolist_dialog(
        title="Select Provider",
        text="Select an LLM provider (ESC to cancel):",
        values=values,
        default=default_provider if default_provider in PROVIDERS else PROVIDERS[0],
    )
    return dialog.run()


async def prompt_for_api_key_interactive(
    ctx: CommandContext | None, provider_name: str, status_text: str
) -> str | None:
    """Zeigt einen maskierten Eingabedialog für den API-Key des Providers."""
    app = ctx.app if ctx else None
    float_container = getattr(app, "float_container", None) if app else None

    if app and float_container:
        return await _show_tui_modal_api_key_dialog(app, float_container, provider_name, status_text)

    dialog = input_dialog(
        title=f"API-Key für {provider_name}",
        text=status_text,
        password=True,
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
        if chosen_provider not in PROVIDERS:
            return CommandResult(
                output=f"Invalid provider '{args[0]}'. Available providers: {', '.join(PROVIDERS)}"
            )
    else:
        current_provider = get_provider()
        chosen_provider = await select_provider_interactive(ctx, current_provider)
        if chosen_provider is None:
            return CommandResult(output="Provider selection cancelled.")

    # Lokale Provider wie Ollama benötigen keine Key-Eingabe
    if chosen_provider == "ollama":
        set_provider(chosen_provider)
        return CommandResult(output=f"Provider switched to: {chosen_provider}")

    # Key-Status abfragen
    cred_store = CredentialsStore.load()
    existing_key = cred_store.get_key(chosen_provider)

    if existing_key:
        masked = f"...{existing_key[-4:]}" if len(existing_key) >= 4 else "gesetzt"
        status_text = f"Aktueller Key: gesetzt (Maskiert: {masked}).\nNeuen Key eingeben zum Überschreiben, oder Enter/ESC zum Beibehalten:"
    else:
        status_text = "Kein API-Key hinterlegt.\nBitte neuen API-Key eingeben:"

    key_input = await prompt_for_api_key_interactive(ctx, chosen_provider, status_text)

    if key_input is None or key_input.strip() == "":
        if existing_key:
            set_provider(chosen_provider)
            return CommandResult(output=f"Provider switched to: {chosen_provider} (kept existing API key).")
        else:
            return CommandResult(
                output=f"Provider switch to '{chosen_provider}' cancelled: No API key provided."
            )

    new_key = key_input.strip()
    cred_store.set_key(chosen_provider, new_key)
    set_provider(chosen_provider)
    return CommandResult(output=f"API key updated. Provider switched to: {chosen_provider}")
