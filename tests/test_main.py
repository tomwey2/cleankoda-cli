import io
import sys
import unittest
from unittest.mock import patch, MagicMock, ANY

from cleankoda.main import main, run_headless

class TestMainDualMode(unittest.TestCase):

    def test_run_headless_slash_command(self):
        import tempfile
        from pathlib import Path
        from cleankoda.memory import Memory

        with tempfile.TemporaryDirectory() as tmpdir:
            mem = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            captured_output = io.StringIO()
            with patch("sys.stdout", captured_output):
                run_headless("/help", mem)
            output = captured_output.getvalue()
            self.assertIn("Available Commands:", output)
            self.assertIn("/exit", output)

    @patch("cleankoda.main.run_agent")
    def test_run_headless_agent_call(self, mock_run_agent):
        import tempfile
        from pathlib import Path
        from cleankoda.memory import Memory

        async def _mock_run_agent(*args, **kwargs):
            yield "Test response from agent"

        mock_run_agent.side_effect = _mock_run_agent

        with tempfile.TemporaryDirectory() as tmpdir:
            mem = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            captured_output = io.StringIO()
            with patch("sys.stdout", captured_output):
                run_headless("What is 1+1?", mem)
            output = captured_output.getvalue()
            self.assertIn("Test response from agent", output)
            mock_run_agent.assert_called_once()

    @patch("cleankoda.main.run_headless")
    def test_main_with_positional_prompt(self, mock_run_headless):
        main(["Explain", "this", "code"])
        mock_run_headless.assert_called_once_with("Explain this code", ANY)

    @patch("cleankoda.main.run_tui")
    def test_main_with_tui_flag(self, mock_run_tui):
        main(["--tui"])
        mock_run_tui.assert_called_once()

    @patch("cleankoda.main.run_headless")
    def test_main_with_piped_input(self, mock_run_headless):
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.read", return_value="Piped input prompt"):
                main([])
                mock_run_headless.assert_called_once_with("Piped input prompt", ANY)

    def test_main_headless_missing_prompt_exits(self):
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(["--headless"])
                self.assertEqual(cm.exception.code, 1)

    def test_status_line_structure(self):
        import tempfile
        from pathlib import Path
        from cleankoda.memory import Memory
        from cleankoda.tui import TUI

        with tempfile.TemporaryDirectory() as tmpdir:
            mem = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            tui = TUI(mem)
            tui.update_status_line()
            lines = tui.status_line.text.splitlines()
            self.assertGreaterEqual(len(lines), 2)
            self.assertIn("Provider:", lines[0])
            self.assertIn("Model:", lines[0])
            self.assertEqual(lines[1], "Ctrl+O for shortcuts")
            self.assertEqual(tui.status_line.window.height, 2)


if __name__ == "__main__":
    unittest.main()
