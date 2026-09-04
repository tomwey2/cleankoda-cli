import asyncio
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import FloatContainer, HSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Frame, TextArea

from cleankoda_cli.commands import CommandContext, registry
from cleankoda_cli.llm_service import stream_chat_response
from cleankoda_cli.memory import Memory
from cleankoda_cli.session_state import SessionState

BANNER = """
▄▄▄▄ █ ▄▄▄  ▄▄▄  ▄▄▄      █ ▄  ▄▄▄▄ ▄▄▄█  ▄▄▄
█    █ █▀▀ █  █  █  █ ▄▄▄ █▀▄  █  █ █  █ █  █
▀▀▀▀ ▀ ▀▀▀ ▀▀▀▀▀ ▀  ▀     ▀  ▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀▀
"""


class TUI:
    """Terminal User Interface Anwendung für cleankoda-cli."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory
        self.showing_shortcuts = False

        self.history_area = TextArea(
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

        self.input_field = TextArea(
            height=3,
            prompt="> ",
            multiline=False,
            wrap_lines=False,
        )

        self.status_line = TextArea(
            height=2,
            text=f"{self.get_session_status_text()}\n? for shortcuts",
            multiline=True,
            wrap_lines=True,
        )

        self.root_container = HSplit([
            self.history_area,
            Frame(self.input_field),
            self.status_line,
        ])

        self.float_container = FloatContainer(content=self.root_container, floats=[])
        self.layout = Layout(self.float_container, focused_element=self.input_field)

        self.kb = KeyBindings()
        self._register_keybindings()

        self.input_field.accept_handler = self._accept_handler

        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
        )
        self.app.float_container = self.float_container

    def get_session_status_text(self) -> str:
        state = SessionState.load()
        return f"Provider: {state.provider} | Model: {state.model} | Temp: {state.temperature}"

    def update_status_line(self) -> None:
        session_text = self.get_session_status_text()
        if self.showing_shortcuts:
            self.status_line.window.height = 5
            self.status_line.text = (
                f"{session_text}\n"
                "Shortcuts & Hilfe (ESC zum Schließen):\n"
                "• Enter   : Nachricht senden\n"
                "• Ctrl+C  : App beenden\n"
                "• Ctrl+Q  : App beenden"
            )
        else:
            self.status_line.window.height = 2
            self.status_line.text = f"{session_text}\n? for shortcuts"

    def _register_keybindings(self) -> None:
        @self.kb.add("c-c")
        @self.kb.add("c-q")
        def _exit(event):
            event.app.exit()

        @self.kb.add("?", eager=True)
        def _show_shortcuts(event):
            self.showing_shortcuts = True
            self.input_field.read_only = True
            self.update_status_line()
            event.app.invalidate()

        @self.kb.add("escape", eager=True)
        def _hide_shortcuts(event):
            self.showing_shortcuts = False
            self.input_field.read_only = False
            self.update_status_line()
            event.app.invalidate()

    def _accept_handler(self, buff) -> None:
        if self.input_field.read_only:
            return
        user_input = self.input_field.text.strip()
        if not user_input:
            return

        self.input_field.text = ""
        asyncio.create_task(self.stream_response(user_input))

    async def stream_response(self, user_text: str) -> None:
        if user_text.startswith("/"):
            ctx = CommandContext(memory=self.memory, app=self.app)
            result = await registry.dispatch_async(user_text, ctx)
            if result.output:
                self.history_area.text += f"\n\n[System]: {result.output}\n"
                self.history_area.buffer.cursor_position = len(self.history_area.text)
                self.app.invalidate()
            self.update_status_line()
            if result.should_exit:
                self.app.exit()
            return

        self.history_area.text += f"\n\n[You]: {user_text}\n[Assistant]: "
        self.history_area.buffer.cursor_position = len(self.history_area.text)
        self.app.invalidate()

        self.memory.add_user(user_text)

        state = SessionState.load()
        chunks = []
        async for chunk in stream_chat_response(self.memory, state):
            chunks.append(chunk)
            self.history_area.text += chunk
            self.history_area.buffer.cursor_position = len(self.history_area.text)
            self.app.invalidate()

        full_response = "".join(chunks)
        if full_response:
            last_msg = self.memory.messages[-1] if self.memory.messages else None
            last_role = last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", None)
            if last_role != "assistant":
                self.memory.add_assistant(full_response)

    def run(self) -> None:
        print("Hello from mini-code!")
        self.update_status_line()
        asyncio.run(self.app.run_async())


def run_tui(memory: Memory) -> None:
    """Startet die interaktive TUI-Anwendung mit der übergebenen Memory-Instanz."""
    tui = TUI(memory)
    tui.run()
