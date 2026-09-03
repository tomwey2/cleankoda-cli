import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import FloatContainer, Window
from prompt_toolkit.layout.layout import Layout

from cleankoda_cli.commands import CommandContext, registry
from cleankoda_cli.config import get_provider
from cleankoda_cli.memory import Memory


class TestProviderCommand(unittest.TestCase):

    def test_command_registered(self):
        cmds = registry.list_commands()
        cmd_names = {c.name for c in cmds}
        self.assertIn("provider", cmd_names)

    def test_provider_direct_argument_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            memory = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            ctx = CommandContext(memory=memory)

            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                res = registry.dispatch("/provider openai", ctx)
                self.assertIn("Provider switched to: openai", res.output)
                self.assertEqual(get_provider(), "openai")

    def test_provider_direct_argument_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            memory = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            ctx = CommandContext(memory=memory)

            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                res = registry.dispatch("/provider unknown_llm", ctx)
                self.assertIn("Invalid provider 'unknown_llm'", res.output)
                self.assertIn("Available providers:", res.output)
                self.assertIsNone(get_provider())

    @patch("cleankoda_cli.commands.provider.select_provider_interactive", new_callable=AsyncMock)
    def test_provider_interactive_selection(self, mock_select):
        mock_select.return_value = "anthropic"
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            memory = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            ctx = CommandContext(memory=memory)

            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                res = registry.dispatch("/provider", ctx)
                self.assertIn("Provider switched to: anthropic", res.output)
                self.assertEqual(get_provider(), "anthropic")
                mock_select.assert_called_once()

    @patch("cleankoda_cli.commands.provider.select_provider_interactive", new_callable=AsyncMock)
    def test_provider_interactive_cancellation(self, mock_select):
        mock_select.return_value = None  # User pressed ESC
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            memory = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            ctx = CommandContext(memory=memory)

            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                res = registry.dispatch("/provider", ctx)
                self.assertIn("Provider selection cancelled.", res.output)
                self.assertIsNone(get_provider())
                mock_select.assert_called_once()

    def test_show_tui_modal_provider_dialog(self):
        from cleankoda_cli.commands.provider import _show_tui_modal_provider_dialog

        float_container = FloatContainer(content=Window(), floats=[])
        layout = Layout(float_container)
        app = Application(layout=layout)

        async def _test():
            task = asyncio.create_task(_show_tui_modal_provider_dialog(app, float_container, "openai"))
            await asyncio.sleep(0.01)

            # Check that float was added
            self.assertEqual(len(float_container.floats), 1)

            # Simulate OK selection via keybinding (bindings[1] is enter)
            dialog_hs = float_container.floats[0].content
            dialog_kb = dialog_hs.key_bindings
            dialog_kb.bindings[1].handler(None)

            res = await task
            self.assertEqual(res, "openai")
            self.assertEqual(len(float_container.floats), 0)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
