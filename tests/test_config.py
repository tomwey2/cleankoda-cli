import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleankoda_cli.config import (
    PROVIDER_MODELS,
    get_model,
    get_models_for_provider,
    get_provider,
    load_config,
    save_config,
    set_model,
    set_provider,
)


class TestConfig(unittest.TestCase):

    def test_load_config_non_existent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                config = load_config()
                self.assertEqual(config, {})
                self.assertIsNone(get_provider())

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                self.assertFalse(config_dir.exists())
                save_config({"provider": "openai", "custom": "value"})

                self.assertTrue(config_dir.exists())
                self.assertTrue(config_file.exists())

                data = load_config()
                self.assertEqual(data.get("provider"), "openai")
                self.assertEqual(data.get("custom"), "value")
                self.assertEqual(get_provider(), "openai")

    def test_set_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                set_provider("anthropic")
                self.assertEqual(get_provider(), "anthropic")

                set_provider("mistral")
                self.assertEqual(get_provider(), "mistral")

                with open(config_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                self.assertEqual(content.get("provider"), "mistral")

    def test_get_models_for_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                self.assertIn("gpt-4o", get_models_for_provider("openai"))
                self.assertIn("claude-3-5-sonnet-latest", get_models_for_provider("anthropic"))

                # Fallback to mistral models if provider unset or unknown
                self.assertEqual(get_models_for_provider("unknown"), PROVIDER_MODELS["mistral"])

    def test_set_and_get_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "cleankoda"
            config_file = config_dir / "config.json"
            with patch("cleankoda_cli.config.CONFIG_DIR", config_dir), patch(
                "cleankoda_cli.config.CONFIG_FILE", config_file
            ):
                set_model("gpt-4o")
                self.assertEqual(get_model(), "gpt-4o")


if __name__ == "__main__":
    unittest.main()
