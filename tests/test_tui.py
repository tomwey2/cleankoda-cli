import unittest
from prompt_toolkit.document import Document
from prompt_toolkit.document import Document
from cleankoda.commands import registry
from cleankoda.tui import SlashCommandCompleter, TUI_STYLE
from cleankoda.memory import Memory


class TestSlashCommandCompleter(unittest.TestCase):

    def setUp(self):
        self.completer = SlashCommandCompleter()

    def test_trigger_on_slash(self):
        doc = Document("/", 1)
        completions = list(self.completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        self.assertIn("/plan", texts)
        self.assertIn("/provider", texts)
        self.assertIn("/model", texts)
        self.assertIn("/clear", texts)
        self.assertIn("/help", texts)
        self.assertIn("/exit", texts)
        for c in completions:
            self.assertEqual(c.start_position, -1)

    def test_prefix_filtering_case_insensitive(self):
        doc = Document("/PROV", 5)
        completions = list(self.completer.get_completions(doc, None))
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, "/provider")
        self.assertEqual(completions[0].display_meta_text, registry._commands["provider"].description)
        self.assertEqual(completions[0].start_position, -5)

    def test_no_completion_without_slash(self):
        doc = Document("hello world", 11)
        completions = list(self.completer.get_completions(doc, None))
        self.assertEqual(len(completions), 0)

    def test_no_completion_after_trailing_space(self):
        doc = Document("/exit ", 6)
        completions = list(self.completer.get_completions(doc, None))
        self.assertEqual(len(completions), 0)


class TestTUIStyleAndConfig(unittest.TestCase):

    def test_tui_style_keys(self):
        style_dict = dict(TUI_STYLE.style_rules)
        # Verify completion menu style rules exist
        style_str = str(TUI_STYLE)
        self.assertTrue(len(TUI_STYLE.style_rules) > 0)


class TestTUIEscapeKeybinding(unittest.TestCase):

    def test_escape_clears_slash_command_prompt(self):
        from unittest.mock import MagicMock
        memory = Memory(system_prompt="Test")
        from cleankoda.tui import TUI
        tui = TUI(memory)
        tui.input_field.text = "/model"

        # Trigger escape keybinding handler
        escape_binding = next(b for b in tui.kb.bindings if b.keys[0].value == "escape" or b.keys[0] == "escape")
        escape_binding.handler(MagicMock())
        self.assertEqual(tui.input_field.text, "")

    def test_escape_preserves_regular_prompt(self):
        from unittest.mock import MagicMock
        memory = Memory(system_prompt="Test")
        from cleankoda.tui import TUI
        tui = TUI(memory)
        tui.input_field.text = "Hello world"

        # Trigger escape keybinding handler
        escape_binding = next(b for b in tui.kb.bindings if b.keys[0].value == "escape" or b.keys[0] == "escape")
        escape_binding.handler(MagicMock())
        self.assertEqual(tui.input_field.text, "Hello world")


class TestTUIEnterCompletionKeybinding(unittest.TestCase):

    from unittest.mock import patch

    @patch("prompt_toolkit.buffer.get_app")
    def test_enter_applies_completion_without_executing(self, mock_get_app):
        from unittest.mock import MagicMock
        from prompt_toolkit.buffer import CompletionState
        from prompt_toolkit.completion import Completion
        from cleankoda.tui import TUI

        mock_app = MagicMock()
        def _close_coro(coro):
            if hasattr(coro, "close"):
                coro.close()
        mock_app.create_background_task.side_effect = _close_coro
        mock_get_app.return_value = mock_app

        memory = Memory(system_prompt="Test")
        tui = TUI(memory)
        tui.input_field.text = "/m"
        tui.input_field.buffer.cursor_position = 2

        comp = Completion("/model", start_position=-2, display="/model")
        state = CompletionState(original_document=tui.input_field.buffer.document, completions=[comp])
        tui.input_field.buffer.complete_state = state

        # Find the enter keybinding registered for completions
        enter_binding = next(b for b in tui.kb.bindings if any(getattr(k, "value", k) in ("c-m", "enter") for k in b.keys))
        mock_event = MagicMock()
        mock_event.current_buffer = tui.input_field.buffer
        enter_binding.handler(mock_event)

        # Verify prompt text is updated to "/model" and complete_state is None
        self.assertEqual(tui.input_field.text, "/model")
        self.assertIsNone(tui.input_field.buffer.complete_state)


if __name__ == "__main__":
    unittest.main()
