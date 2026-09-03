import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleankoda_cli.config import get_provider, load_config, save_config, set_provider


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
                self.assertEqual(content, {"provider": "mistral"})


if __name__ == "__main__":
    unittest.main()
