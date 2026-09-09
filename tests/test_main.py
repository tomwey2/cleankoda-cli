import io
import sys
import unittest
from unittest.mock import patch, MagicMock, ANY

from cleankoda.agent import Agent
from cleankoda.llm import LLMService
from cleankoda.main import main, run_headless
from cleankoda.memory import Memory
from cleankoda.session_state import SessionState
from cleankoda.tools import TOOL_SCHEMAS


class TestMainDualMode(unittest.TestCase):

    def test_run_headless_slash_command(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            mem = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            agent = Agent(
                memory=mem,
                llm_service=LLMService(),
                tools=TOOL_SCHEMAS,
                state=SessionState.load(),
            )
            captured_output = io.StringIO()
            with patch("sys.stdout", captured_output):
                run_headless("/help", agent=agent)
            output = captured_output.getvalue()
            self.assertIn("Available Commands:", output)
            self.assertIn("/exit", output)

    @patch("cleankoda.agent.Agent.run")
    def test_run_headless_agent_call(self, mock_agent_run):
        import tempfile
        from pathlib import Path

        async def _mock_run_agent(*args, **kwargs):
            yield "Test response from agent"

        mock_agent_run.side_effect = _mock_run_agent

        with tempfile.TemporaryDirectory() as tmpdir:
            mem = Memory(system_prompt="Test", file=Path(tmpdir) / "mem.json")
            agent = Agent(
                memory=mem,
                llm_service=LLMService(),
                tools=TOOL_SCHEMAS,
                state=SessionState.load(),
            )
            captured_output = io.StringIO()
            with patch("sys.stdout", captured_output):
                run_headless("What is 1+1?", agent=agent)
            output = captured_output.getvalue()
            self.assertIn("Test response from agent", output)
            mock_agent_run.assert_called_once()

    @patch("cleankoda.main.run_headless")
    def test_main_with_positional_prompt(self, mock_run_headless):
        main(["Explain", "this", "code"])
        mock_run_headless.assert_called_once_with("Explain this code", agent=ANY)

    @patch("cleankoda.main.run_tui")
    def test_main_with_tui_flag(self, mock_run_tui):
        main(["--tui"])
        mock_run_tui.assert_called_once_with(ANY)

    @patch("cleankoda.main.run_headless")
    def test_main_with_piped_input(self, mock_run_headless):
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.read", return_value="Piped input prompt"):
                main([])
                mock_run_headless.assert_called_once_with("Piped input prompt", agent=ANY)

    def test_main_headless_missing_prompt_exits(self):
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(["--headless"])
                self.assertEqual(cm.exception.code, 1)

    def test_status_line_structure(self):
        import tempfile
        from pathlib import Path
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
