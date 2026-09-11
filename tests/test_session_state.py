import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleankoda.config import AppConfig, get_config_file
from cleankoda.llm import CredentialsStore


class TestAppConfig(unittest.TestCase):

    def test_default_values(self):
        cfg = AppConfig()
        self.assertEqual(cfg.provider, "mistral")
        self.assertEqual(cfg.model, "mistral-small-latest")
        self.assertEqual(cfg.temperature, 0.2)
        self.assertEqual(cfg.max_tokens, 4096)
        self.assertFalse(hasattr(cfg, "api_keys"))

    def test_litellm_model_identifier(self):
        cfg = AppConfig(provider="ollama", model="llama3.3")
        self.assertEqual(cfg.litellm_model_identifier, "ollama/llama3.3")

        cfg = AppConfig(provider="anthropic", model="claude-3-5-sonnet-latest")
        self.assertEqual(cfg.litellm_model_identifier, "anthropic/claude-3-5-sonnet-latest")

        cfg = AppConfig(provider="google", model="gemini-2.5-flash")
        self.assertEqual(cfg.litellm_model_identifier, "gemini/gemini-2.5-flash")

        cfg = AppConfig(provider="openrouter", model="anthropic/claude-3")
        self.assertEqual(cfg.litellm_model_identifier, "anthropic/claude-3")

        cfg = AppConfig(provider="openai", model="gpt-4o")
        self.assertEqual(cfg.litellm_model_identifier, "openai/gpt-4o")

    def test_get_active_api_key_delegation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / "credentials.json"
            store = CredentialsStore(keys={"openai": "key_in_cred_store"})
            store.save(file_path=cred_file)

            cfg = AppConfig(provider="openai")

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(cfg.get_active_api_key(credentials_file=cred_file), "key_in_cred_store")

            with patch.dict(os.environ, {"OPENAI_API_KEY": "key_in_env"}):
                self.assertEqual(cfg.get_active_api_key(credentials_file=cred_file), "key_in_env")

    def test_save_and_load_persistence_and_permissions(self):
        file_path = get_config_file()
        cfg = AppConfig(provider="anthropic", model="claude-3-5-haiku-latest", temperature=0.5)
        cfg.save()

        self.assertTrue(file_path.exists())

        # Permissions check 0o600
        file_stat = file_path.stat()
        file_mode = stat.S_IMODE(file_stat.st_mode)
        self.assertEqual(file_mode, 0o600)

        loaded_cfg = AppConfig.load()
        self.assertEqual(loaded_cfg.provider, "anthropic")
        self.assertEqual(loaded_cfg.model, "claude-3-5-haiku-latest")
        self.assertEqual(loaded_cfg.temperature, 0.5)


if __name__ == "__main__":
    unittest.main()
