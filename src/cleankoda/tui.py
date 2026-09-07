import asyncio
import re
from prompt_toolkit.application import Application
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.filters import completion_is_selected, has_completions
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea

from cleankoda.commands import CommandContext, registry
from cleankoda.llm import stream_chat_response
from cleankoda.memory import Memory
from cleankoda.session_state import SessionState
from cleankoda.tools import get_sandbox_status, sandbox_manager

BANNER = """
  ▄▄▄ █  ▄▄▄   ▄▄▄  ▄▄▄▄  █  ▄  ▄▄▄  ▄▄▄█  ▄▄▄
 █    █ █▄▄▄█  ▄▄▄█ █   █ █▄▀  █   █ █  █  ▄▄▄█
 ▀▄▄▄ █ ▀▄▄▄▄ ▀▄▄▄█ █   █ █ ▀▄ ▀▄▄▄▀ █▄▄█ ▀▄▄▄█
"""

TUI_STYLE = Style.from_dict({
    "completion-menu": "bg:#d0d0d0 #000000",
    "completion-menu.completion": "bg:#d0d0d0 #000000",
    "completion-menu.completion.current": "bg:#005f87 #ffffff noreverse bold",
    "completion-menu.meta": "bg:#d0d0d0 #555555",
    "completion-menu.meta.completion": "bg:#d0d0d0 #555555",
    "completion-menu.meta.completion.current": "bg:#005f87 #ffffff noreverse",
    "completion-menu.completion.current.meta": "bg:#005f87 #ffffff noreverse",
})


class SlashCommandCompleter(Completer):
    """Autocompleter for slash commands in the TUI input line."""

    def __init__(self, commands: dict[str, str] | None = None) -> None:
        self._commands = commands

    def _get_commands(self) -> dict[str, str]:
        if self._commands is not None:
            return self._commands
        return {f"/{cmd.name}": cmd.description for cmd in registry.list_commands()}

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor

        if text_before_cursor.startswith("/sandbox "):
            parts = text_before_cursor.split()
            word = parts[-1] if len(parts) > 1 and not text_before_cursor.endswith(" ") else ""
            word_lower = word.lower()
            if "off".startswith(word_lower):
                yield Completion(
                    text="off",
                    start_position=-len(word),
                    display="off",
                    display_meta="Sandbox deaktivieren (HostRunner)",
                )
            return

        if text_before_cursor.endswith((" ", "\t", "\n")):
            word = ""
        else:
            words = text_before_cursor.split()
            word = words[-1] if words else text_before_cursor

        if not word.startswith("/"):
            return

        commands_map = self._get_commands()
        word_lower = word.lower()
        for cmd, desc in commands_map.items():
            if cmd.lower().startswith(word_lower):
                yield Completion(
                    text=cmd,
                    start_position=-len(word),
                    display=cmd,
                    display_meta=desc,
                )


class ChatLexer(Lexer):
    """Lexer that styles user lines starting with '>' in bold and parses inline Markdown formatting live."""

    def lex_document(self, document):
        pattern = re.compile(r"(\*\*.*?\*\*|\*.*?\*|`.*?`)")

        def get_line(lineno):
            line = document.lines[lineno]
            if line.startswith(">"):
                return [("bold", line)]

            parts = pattern.split(line)
            result = []
            for part in parts:
                if not part:
                    continue
                if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                    result.append(("bold", part[2:-2]))
                elif part.startswith("*") and part.endswith("*") and len(part) >= 2:
                    result.append(("italic", part[1:-1]))
                elif part.startswith("`") and part.endswith("`") and len(part) >= 2:
                    result.append(("underline", part[1:-1]))
                else:
                    result.append(("", part))
            return result

        return get_line


class TUI:
    """Terminal User Interface application for cleankoda cli."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory
        self.showing_shortcuts = False
        self.is_processing = False
        self.cancel_event = asyncio.Event()

        self.history_area = TextArea(
            text=BANNER
            + " Welcome to cleankoda!\n"
            + " The coding agent for clean code software development.\n"
            + ("─" * 60)
            + "\n",
            scrollbar=True,
            read_only=True,
            wrap_lines=True,
            focusable=False,
            lexer=ChatLexer(),
        )

        self.input_field = TextArea(
            height=3,
            prompt="> ",
            multiline=False,
            wrap_lines=False,
            completer=SlashCommandCompleter(),
            complete_while_typing=True,
            auto_suggest=AutoSuggestFromHistory(),
        )

        self.status_line = TextArea(
            height=2,
            text=f"{self.get_session_status_text()}\nCtrl+O for shortcuts",
            multiline=True,
            wrap_lines=True,
        )

        self.root_container = HSplit([
            self.history_area,
            Frame(self.input_field),
            self.status_line,
        ])

        self.float_container = FloatContainer(
            content=self.root_container,
            floats=[
                Float(
                    content=CompletionsMenu(max_height=8, scroll_offset=1),
                    xcursor=True,
                    ycursor=True,
                )
            ],
        )
        self.layout = Layout(self.float_container, focused_element=self.input_field)

        self.kb = KeyBindings()
        self._register_keybindings()

        self.input_field.accept_handler = self._accept_handler

        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=False,
            style=TUI_STYLE,
        )
        self.app.float_container = self.float_container

    def get_session_status_text(self) -> str:
        state = SessionState.load()
        sb_status = get_sandbox_status()
        return f"Provider: {state.provider} | Model: {state.model} | Temp: {state.temperature} | Sandbox: {sb_status}"

    def update_status_line(self, custom_status: str | None = None) -> None:
        session_text = self.get_session_status_text()
        if self.showing_shortcuts:
            self.status_line.window.height = 5
            self.status_line.text = (
                f"{session_text}\n"
                "Shortcuts & Help (ESC to close):\n"
                "• Enter   : Send message\n"
                "• Ctrl+C  : Exit application\n"
                "• Ctrl+Q  : Exit application"
            )
        elif custom_status:
            self.status_line.window.height = 2
            self.status_line.text = f"{session_text}\n{custom_status}"
        else:
            self.status_line.window.height = 2
            self.status_line.text = f"{session_text}\nCtrl+O for shortcuts"

    def _register_keybindings(self) -> None:
        @self.kb.add("c-c")
        @self.kb.add("c-q")
        def _exit(event):
            event.app.exit()

        @self.kb.add("c-o", eager=True)
        def _show_shortcuts(event):
            self.showing_shortcuts = True
            self.input_field.read_only = True
            self.update_status_line()
            event.app.invalidate()

        @self.kb.add("escape", eager=True)
        def _handle_escape(event):
            if self.is_processing:
                self.cancel_event.set()
            if self.input_field.text.lstrip().startswith("/"):
                self.input_field.text = ""
            self.showing_shortcuts = False
            if not self.is_processing:
                self.input_field.read_only = False
            self.update_status_line()
            event.app.invalidate()

        @self.kb.add("enter", filter=has_completions | completion_is_selected)
        def _accept_completion(event):
            buff = event.current_buffer
            if buff.complete_state:
                completion = buff.complete_state.current_completion
                if completion is None and buff.complete_state.completions:
                    completion = buff.complete_state.completions[0]
                if completion:
                    buff.apply_completion(completion)
                buff.complete_state = None

    def _accept_handler(self, buff) -> None:
        if self.input_field.read_only or self.is_processing:
            return
        user_input = self.input_field.text.strip()
        if not user_input:
            return

        self.input_field.text = ""
        asyncio.create_task(self._safe_stream_response(user_input))

    async def _safe_stream_response(self, user_text: str) -> None:
        self.is_processing = True
        self.input_field.read_only = True
        try:
            await self.stream_response(user_text)
        except Exception as e:
            self.history_area.text += f"\n\n[Error]: {e}\n"
            self.history_area.buffer.cursor_position = len(self.history_area.text)
        finally:
            self.is_processing = False
            self.update_status_line(None)
            if not self.showing_shortcuts:
                self.input_field.read_only = False
            self.app.invalidate()

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

        formatted_user = "\n".join(f"> {line}" for line in user_text.splitlines()) if user_text else f"> {user_text}"
        self.history_area.text += f"\n\n{formatted_user}\n\n  "
        self.history_area.buffer.cursor_position = len(self.history_area.text)
        self.app.invalidate()

        self.memory.add_user(user_text)

        self.cancel_event.clear()

        def status_cb(status_text: str | None) -> None:
            self.update_status_line(status_text)
            self.app.invalidate()

        state = SessionState.load()
        async for chunk in stream_chat_response(
            self.memory, state, cancel_event=self.cancel_event, status_callback=status_cb
        ):
            indented_chunk = chunk.replace("\n", "\n  ")
            self.history_area.text += indented_chunk
            self.history_area.buffer.cursor_position = len(self.history_area.text)
            self.app.invalidate()

    def run(self) -> None:
        self.update_status_line()
        try:
            asyncio.run(self.app.run_async())
        finally:
            sandbox_manager.stop()


def run_tui(memory: Memory) -> None:
    """Start the interactive TUI application with the provided Memory instance."""
    tui = TUI(memory)
    tui.run()
