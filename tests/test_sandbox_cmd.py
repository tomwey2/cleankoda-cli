import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from prompt_toolkit.application import Application
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import FloatContainer, Window
from prompt_toolkit.layout.layout import Layout

from cleankoda.commands import CommandContext, registry
from cleankoda.memory import Memory
from cleankoda.sandbox import AVAILABLE_IMAGES
from cleankoda.tools.tool_registry import (
    get_sandbox_status,
    switch_runner,
)
from cleankoda.tui import SlashCommandCompleter


class TestSandboxCommand(unittest.TestCase):

    def setUp(self):
        # Reset to host runner before each test
        asyncio.run(switch_runner(use_sandbox_param=False))

    def test_sandbox_command_registered(self):
        cmds = registry.list_commands()
        cmd_names = {c.name for c in cmds}
        self.assertIn("sandbox", cmd_names)

    def test_sandbox_off_direct(self):
        asyncio.run(switch_runner(use_sandbox_param=False))
        ctx = CommandContext(memory=Memory(system_prompt="Test"))
        res = registry.dispatch("/sandbox off", ctx)
        self.assertIn("Sandbox deaktiviert", res.output)
        self.assertEqual(get_sandbox_status(), "host")

    @patch("cleankoda.sandbox.manager.DockerSandbox")
    def test_sandbox_image_direct(self, mock_docker_sandbox):
        mock_instance = MagicMock()
        mock_instance.image = "node:20-slim"
        mock_instance.start_async = AsyncMock()
        mock_docker_sandbox.return_value = mock_instance

        ctx = CommandContext(memory=Memory(system_prompt="Test"))
        res = registry.dispatch("/sandbox node:20-slim", ctx)
        self.assertIn("Sandbox aktiv: Image [node:20-slim]", res.output)
        self.assertEqual(get_sandbox_status(), "node:20-slim")
        mock_instance.start_async.assert_awaited_once()

    @patch("cleankoda.sandbox.manager.DockerSandbox")
    def test_sandbox_docker_error_fallback(self, mock_docker_sandbox):
        mock_instance = MagicMock()
        mock_instance.start_async = AsyncMock(side_effect=RuntimeError("Docker daemon not reachable"))
        mock_docker_sandbox.return_value = mock_instance

        ctx = CommandContext(memory=Memory(system_prompt="Test"))
        res = registry.dispatch("/sandbox python:3.12-slim", ctx)
        self.assertIn("Fehler beim Starten der Sandbox", res.output)
        self.assertIn("Fallback auf Host-System", res.output)
        self.assertEqual(get_sandbox_status(), "host")

    def test_sandbox_interactive_selection_in_tui(self):
        from cleankoda.commands.sandbox import _show_tui_modal_sandbox_dialog

        float_container = FloatContainer(content=Window(), floats=[])
        layout = Layout(float_container)
        app = Application(layout=layout)

        async def _test():
            task = asyncio.create_task(
                _show_tui_modal_sandbox_dialog(app, float_container, "python:3.11-slim")
            )
            await asyncio.sleep(0.01)

            self.assertEqual(len(float_container.floats), 1)

            # Trigger enter keybinding (index 1) on dialog
            dialog_hs = float_container.floats[0].content
            dialog_kb = dialog_hs.key_bindings
            dialog_kb.bindings[1].handler(None)

            res = await task
            self.assertEqual(res, AVAILABLE_IMAGES[0].id)
            self.assertEqual(len(float_container.floats), 0)

        asyncio.run(_test())

    def test_sandbox_autocompleter(self):
        completer = SlashCommandCompleter()
        doc = Document("/sandbox ", 9)
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        self.assertIn("off", texts)


if __name__ == "__main__":
    unittest.main()
