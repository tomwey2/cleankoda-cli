import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleankoda.config import (
    get_model,
    get_models_for_provider,
    get_provider,
    load_session_state,
    save_session_state,
    set_model,
    set_provider,
)
from cleankoda.llm.config import PROVIDER_MODELS, PROVIDERS
from cleankoda.session_state import SessionState


class TestConfig(unittest.TestCase):

    def test_llm_config_providers(self):
        self.assertIn("mistral", PROVIDERS)
        self.assertIn("openai", PROVIDERS)
        self.assertIn("anthropic", PROVIDERS)
        self.assertIn("ollama", PROVIDERS)
        self.assertIn("google", PROVIDERS)
        self.assertIn("mistral", PROVIDER_MODELS)

    def test_load_session_state_non_existent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda.config.CONFIG_DIR", config_dir), patch(
                "cleankoda.config.CONFIG_FILE", config_file
            ):
                state = load_session_state()
                self.assertEqual(state.provider, "mistral")
                self.assertIsNone(get_provider())

    def test_save_and_load_session_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda.config.CONFIG_DIR", config_dir), patch(
                "cleankoda.config.CONFIG_FILE", config_file
            ):
                self.assertFalse(config_dir.exists())
                state = SessionState(provider="openai", model="gpt-4o")
                save_session_state(state)

                self.assertTrue(config_dir.exists())
                self.assertTrue(config_file.exists())

                loaded_state = load_session_state()
                self.assertEqual(loaded_state.provider, "openai")
                self.assertEqual(loaded_state.model, "gpt-4o")
                self.assertEqual(get_provider(), "openai")

    def test_set_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda.config.CONFIG_DIR", config_dir), patch(
                "cleankoda.config.CONFIG_FILE", config_file
            ):
                set_provider("anthropic")
                self.assertEqual(get_provider(), "anthropic")
                self.assertEqual(get_model(), "claude-3-5-sonnet-latest")

                set_provider("mistral")
                self.assertEqual(get_provider(), "mistral")
                self.assertEqual(get_model(), "mistral-small-latest")

                with open(config_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                self.assertEqual(content.get("provider"), "mistral")
                self.assertEqual(content.get("model"), "mistral-small-latest")

    def test_get_models_for_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda.config.CONFIG_DIR", config_dir), patch(
                "cleankoda.config.CONFIG_FILE", config_file
            ):
                self.assertIn("gpt-4o", get_models_for_provider("openai"))
                self.assertIn("claude-3-5-sonnet-latest", get_models_for_provider("anthropic"))

                # Fallback to mistral models if provider unset or unknown
                self.assertEqual(get_models_for_provider("unknown"), PROVIDER_MODELS["mistral"])

    def test_set_and_get_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda.config.CONFIG_DIR", config_dir), patch(
                "cleankoda.config.CONFIG_FILE", config_file
            ):
                set_model("gpt-4o")
                self.assertEqual(get_model(), "gpt-4o")


if __name__ == "__main__":
    unittest.main()
