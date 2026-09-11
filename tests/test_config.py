import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleankoda.config import AppConfig, get_config_file
from cleankoda.llm.config import PROVIDER_MODELS, PROVIDERS, get_models_for_provider


class TestConfig(unittest.TestCase):

    def test_llm_config_providers(self):
        self.assertIn("mistral", PROVIDERS)
        self.assertIn("openai", PROVIDERS)
        self.assertIn("anthropic", PROVIDERS)
        self.assertIn("ollama", PROVIDERS)
        self.assertIn("google", PROVIDERS)
        self.assertIn("mistral", PROVIDER_MODELS)

    def test_app_config_load_non_existent(self):
        config_file = get_config_file()
        self.assertFalse(config_file.exists())
        config = AppConfig.load()
        self.assertEqual(config.provider, "mistral")
        self.assertEqual(config.model, "mistral-small-latest")
        self.assertTrue(config_file.exists())

    def test_app_config_save_and_load(self):
        config_file = get_config_file()
        config = AppConfig(provider="openai", model="gpt-4o")
        config.save()

        self.assertTrue(config_file.exists())

        loaded_config = AppConfig.load()
        self.assertEqual(loaded_config.provider, "openai")
        self.assertEqual(loaded_config.model, "gpt-4o")

        with open(config_file, "r", encoding="utf-8") as f:
            content = json.load(f)
        self.assertEqual(content.get("provider"), "openai")
        self.assertEqual(content.get("model"), "gpt-4o")

    def test_get_models_for_provider(self):
        self.assertIn("gpt-4o", get_models_for_provider("openai"))
        self.assertIn("claude-3-5-sonnet-latest", get_models_for_provider("anthropic"))
        self.assertEqual(get_models_for_provider("unknown"), PROVIDER_MODELS["mistral"])


if __name__ == "__main__":
    unittest.main()

