import io
import sys
import unittest
from unittest.mock import patch, MagicMock

from cleankoda_cli.llm import model_name
from cleankoda_cli.tui import main, run_headless

class TestCLIDualMode(unittest.TestCase):

    def test_run_headless_slash_command(self):
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            run_headless("/help")
        output = captured_output.getvalue()
        self.assertIn("Available Commands:", output)
        self.assertIn("/exit", output)

    @patch("cleankoda_cli.tui.run_agent")
    def test_run_headless_agent_call(self, mock_run_agent):
        mock_run_agent.return_value = "Test response from agent"
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            run_headless("What is 1+1?")
        output = captured_output.getvalue()
        self.assertIn("Test response from agent", output)
        mock_run_agent.assert_called_once()

    @patch("cleankoda_cli.tui.run_headless")
    def test_main_with_positional_prompt(self, mock_run_headless):
        main(["Explain", "this", "code"])
        mock_run_headless.assert_called_once_with("Explain this code")

    @patch("cleankoda_cli.tui.run_tui")
    def test_main_with_tui_flag(self, mock_run_tui):
        main(["--tui"])
        mock_run_tui.assert_called_once_with()

    @patch("cleankoda_cli.tui.run_headless")
    def test_main_with_piped_input(self, mock_run_headless):
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.read", return_value="Piped input prompt"):
                main([])
                mock_run_headless.assert_called_once_with("Piped input prompt")

    def test_main_headless_missing_prompt_exits(self):
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    main(["--headless"])
                self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
