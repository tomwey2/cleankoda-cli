import asyncio
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit
from prompt_toolkit.widgets import Button, Dialog, RadioList

from cleankoda.commands.command_registry import CommandContext, CommandResult, registry
from cleankoda.config import config
from cleankoda.sandbox import AVAILABLE_IMAGES


async def _show_tui_modal_sandbox_dialog(
    app: Application,
    float_container: FloatContainer,
    current_status: str,
) -> str | None:
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    values = [(img.id, f"{img.id} - {img.description}") for img in AVAILABLE_IMAGES]
    default_val = (
        current_status
        if any(img.id == current_status for img in AVAILABLE_IMAGES)
        else AVAILABLE_IMAGES[0].id
    )
    radio_list = RadioList(values=values, default=default_val)

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
        title="Select Sandbox Environment",
        body=radio_list,
        buttons=[
            Button("OK", handler=on_ok),
            Button("Cancel", handler=on_cancel),
        ],
        width=65,
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


async def select_sandbox_interactive(
    ctx: CommandContext | None = None,
    current_status: str | None = None,
) -> str | None:
    """Interaktiver Dialog zur Sandbox-Auswahl (TUI Modal)."""
    app = ctx.app if ctx else None
    float_container = getattr(app, "float_container", None) if app else None

    if app and float_container:
        sandbox = getattr(ctx.agent, "sandbox", None) if ctx else None
        status = current_status or (sandbox.get_sandbox_image().id if sandbox else "host")
        return await _show_tui_modal_sandbox_dialog(app, float_container, status)

    return None


@registry.register(
    "sandbox",
    description="Konfiguriert die Docker-Sandbox oder schaltet sie aus",
    usage="/sandbox [off|image_name]",
)
async def cmd_sandbox(args: list[str], ctx: CommandContext) -> CommandResult:
    """Slash-Command Handler für /sandbox."""
    sandbox = getattr(ctx.agent, "sandbox", None) if ctx and ctx.agent else None
    if not sandbox:
        return CommandResult(output="Error: Sandbox is not available in command context.")

    if args:
        target = args[0].strip()
    else:
        target = await select_sandbox_interactive(ctx)
        if target is None:
            return CommandResult(output="Sandbox-Auswahl abgebrochen.")

    if target.lower() in ("off", "host"):
        msg = await sandbox.switch_runner(False)
        config.sandbox = "host"
        config.save()
    else:
        # Sofort Statuszeile aktualisieren
        sandbox.is_starting = True
        if ctx.app:
            ctx.app.invalidate()

        msg = await sandbox.switch_runner(True, target)
        config.sandbox = target
        config.save()

    if ctx.app:
        ctx.app.invalidate()

    return CommandResult(output=msg)
