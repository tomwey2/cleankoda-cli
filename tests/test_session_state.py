import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleankoda.llm import CredentialsStore
from cleankoda.statusline import SessionState


class TestSessionState(unittest.TestCase):

    def test_default_values(self):
        state = SessionState()
        self.assertEqual(state.provider, "mistral")
        self.assertEqual(state.model, "mistral-medium-latest")
        self.assertEqual(state.temperature, 0.2)
        self.assertEqual(state.max_tokens, 4096)
        self.assertFalse(hasattr(state, "api_keys"))

    def test_litellm_model_identifier(self):
        state = SessionState(provider="ollama", model="llama3.3")
        self.assertEqual(state.litellm_model_identifier, "ollama/llama3.3")

        state = SessionState(provider="anthropic", model="claude-3-5-sonnet-latest")
        self.assertEqual(state.litellm_model_identifier, "anthropic/claude-3-5-sonnet-latest")

        state = SessionState(provider="google", model="gemini-2.5-flash")
        self.assertEqual(state.litellm_model_identifier, "gemini/gemini-2.5-flash")

        state = SessionState(provider="openrouter", model="anthropic/claude-3")
        self.assertEqual(state.litellm_model_identifier, "anthropic/claude-3")

        state = SessionState(provider="openai", model="gpt-4o")
        self.assertEqual(state.litellm_model_identifier, "openai/gpt-4o")

    def test_get_active_api_key_delegation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / "credentials.json"
            store = CredentialsStore(keys={"openai": "key_in_cred_store"})
            store.save(file_path=cred_file)

            state = SessionState(provider="openai")

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(state.get_active_api_key(credentials_file=cred_file), "key_in_cred_store")

            with patch.dict(os.environ, {"OPENAI_API_KEY": "key_in_env"}):
                self.assertEqual(state.get_active_api_key(credentials_file=cred_file), "key_in_env")

    def test_legacy_api_keys_migration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            cred_file = Path(tmpdir) / "credentials.json"

            # Create legacy config.json with api_keys
            legacy_data = {
                "provider": "openai",
                "model": "gpt-4o",
                "api_keys": {"openai": "legacy-sk-openai"}
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f)

            state = SessionState.load(file_path=config_file, credentials_file=cred_file)
            self.assertEqual(state.provider, "openai")

            # Verify credentials.json received the legacy key
            cred_store = CredentialsStore.load(file_path=cred_file)
            self.assertEqual(cred_store.get_stored_key("openai"), "legacy-sk-openai")

            # Verify config.json no longer contains api_keys
            with open(config_file, "r", encoding="utf-8") as f:
                new_config_data = json.load(f)
            self.assertNotIn("api_keys", new_config_data)

    def test_save_and_load_persistence_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "config.json"
            state = SessionState(provider="anthropic", model="claude-3-5-haiku-latest", temperature=0.5)
            state.save(file_path=file_path)

            self.assertTrue(file_path.exists())

            # Permissions check 0o600
            file_stat = file_path.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)
            self.assertEqual(file_mode, 0o600)

            loaded_state = SessionState.load(file_path=file_path)
            self.assertEqual(loaded_state.provider, "anthropic")
            self.assertEqual(loaded_state.model, "claude-3-5-haiku-latest")
            self.assertEqual(loaded_state.temperature, 0.5)


if __name__ == "__main__":
    unittest.main()
