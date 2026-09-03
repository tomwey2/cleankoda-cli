import argparse
import asyncio
import sys
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import FloatContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Frame, TextArea

from cleankoda_cli.agent import SYSTEM_PROMPT, run_agent
from cleankoda_cli.commands import CommandContext, registry
from cleankoda_cli.memory import Memory
from cleankoda_cli.llm import model_name

# Memory instanziieren
memory = Memory(system_prompt=SYSTEM_PROMPT, file=".agents/memory.json")

BANNER = """
▄▄▄▄ █ ▄▄▄  ▄▄▄  ▄▄▄      █ ▄  ▄▄▄▄ ▄▄▄█  ▄▄▄
█    █ █▀▀ █  █  █  █ ▄▄▄ █▀▄  █  █ █  █ █  █
▀▀▀▀ ▀ ▀▀▀ ▀▀▀▀▀ ▀  ▀     ▀  ▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀▀
"""

# 1. Widgets definieren
# Oberer Bereich: Scrollbarer Verlauf / Ausgabefenster
history_area = TextArea(
    text=BANNER
    + "Welcome to cleankoda-cli!\n"
    + "The coding agent for clean code software development.\n"
    + ("─" * 60)
    + "\n",
    scrollbar=True,
    read_only=True,
    wrap_lines=True,
    focusable=False,
)

# Unterer Bereich: Fixierte Eingabezeile
input_field = TextArea(
    height=3,
    prompt="> ",
    multiline=False,
    wrap_lines=False,
)

# Unterer Bereich: Fixierte Eingabezeile
status_line = TextArea(
    height=1,
    text="? for shortcuts",
    multiline=True,
    wrap_lines=True,
)

# 2. Layout aufbauen (Vertikaler Split: Verlauf oben, Eingabe unten im Rahmen)
root_container = HSplit([
    history_area,
    Frame(input_field),
    status_line
])

float_container = FloatContainer(content=root_container, floats=[])
layout = Layout(float_container, focused_element=input_field)

# 3. Keybindings
kb = KeyBindings()

@kb.add("c-c")
@kb.add("c-q")
def _exit(event):
    """Beendet die App sauber."""
    event.app.exit()

@kb.add("?", eager=True)
def _show_shortcuts(event):
    input_field.read_only = True
    status_line.window.height = 3
    status_line.text = (
        "Shortcuts & Hilfe (ESC zum Schließen):\n"
        "• Enter   : Nachricht senden\n"
        "• Ctrl+C  : App beenden\n"
        "• Ctrl+Q  : App beenden"
    )
    event.app.invalidate()

@kb.add("escape", eager=True)
def _hide_shortcuts(event):
    input_field.read_only = False
    status_line.window.height = 1
    status_line.text = "? for shortcuts"
    event.app.invalidate()

# 4. LLM-Stream & Agent Integration
async def stream_response(app: Application, user_text: str):
    # Fast path for slash commands
    if user_text.startswith("/"):
        ctx = CommandContext(memory=memory, app=app)
        result = await registry.dispatch_async(user_text, ctx)
        if result.output:
            history_area.text += f"\n\n[System]: {result.output}\n"
            history_area.buffer.cursor_position = len(history_area.text)
            app.invalidate()
        if result.should_exit:
            app.exit()
        return

    # Nutzer-Eingabe zum Verlauf hinzufügen
    history_area.text += f"\n\n[You]: {user_text}\n[Assistant]: "
    history_area.buffer.cursor_position = len(history_area.text)
    app.invalidate()  # UI neu zeichnen

    # Nutzer-Eingabe zur Memory hinzufügen
    memory.add_user(user_text)

    # run_agent mit der Memory aufrufen
    response_text = await asyncio.to_thread(run_agent, memory)

    if response_text:
        # Antwort Zeichen für Zeichen in die UI streamen
        for char in str(response_text):
            await asyncio.sleep(0.01)
            history_area.text += char
            history_area.buffer.cursor_position = len(history_area.text)
            app.invalidate()  # Erzwingt Redraw im Terminal-Buffer

def accept_handler(buff):
    """Wird aufgerufen, wenn Enter gedrückt wird."""
    if input_field.read_only:
        return
    user_input = input_field.text.strip()
    if not user_input:
        return

    # Eingabefeld leeren
    input_field.text = ""

    # Streaming asynchron im Hintergrund starten
    asyncio.create_task(stream_response(app, user_input))

input_field.accept_handler = accept_handler

# 5. Application starten (full_screen=True schaltet in den Alternate Screen)
app = Application(
    layout=layout,
    key_bindings=kb,
    full_screen=True,  # Lässt die CLI wie eine native App wirken
    mouse_support=True,
)
app.float_container = float_container

def run_headless(prompt_text: str) -> None:
    """Führt den Prompt im Headless-Modus (ohne TUI) aus."""
    mem = Memory(system_prompt=SYSTEM_PROMPT, file=".agents/memory.json")

    # Slash-Command Check
    if prompt_text.startswith("/"):
        ctx = CommandContext(memory=mem)
        result = registry.dispatch(prompt_text, ctx)
        if result.output:
            print(result.output)
        return

    mem.add_user(prompt_text)
    response = run_agent(mem)
    if response:
        print(response)

def run_tui() -> None:
    """Startet die interaktive TUI-Anwendung."""
    print("Hello from mini-code!")
    asyncio.run(app.run_async())

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="mini-code CLI")
    parser.add_argument("prompt_pos", nargs="*", help="Optionaler Prompt (Headless)")
    parser.add_argument("-p", "--prompt", help="Prompt für den Headless-Modus")
    parser.add_argument("--headless", action="store_true", help="Erzwingt Headless-Modus")
    parser.add_argument("--tui", action="store_true", help="Erzwingt TUI-Modus")

    args = parser.parse_args(argv)
    prompt_parts = args.prompt_pos if args.prompt_pos else []
    pos_prompt = " ".join(prompt_parts).strip() if prompt_parts else None
    prompt = args.prompt or pos_prompt

    piped_input = None
    if not sys.stdin.isatty():
        try:
            piped_input = sys.stdin.read().strip()
        except OSError:
            piped_input = None

    final_prompt = prompt or piped_input

    if args.tui:
        run_tui()
    elif args.headless or final_prompt is not None:
        if not final_prompt:
            print("Error: Headless mode requires a prompt argument or piped standard input.", file=sys.stderr)
            sys.exit(1)
        run_headless(final_prompt)
    else:
        run_tui()

if __name__ == "__main__":
    main()
