import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleankoda.llm import CredentialsStore


class TestCredentialsStore(unittest.TestCase):

    def test_default_credentials_store(self):
        store = CredentialsStore()
        self.assertEqual(store.keys, {})

    def test_save_load_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "credentials.json"
            store = CredentialsStore(keys={"openai": "sk-123456789"})
            store.save(file_path=file_path)

            self.assertTrue(file_path.exists())

            # Check permissions 0o600
            file_stat = file_path.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)
            self.assertEqual(file_mode, 0o600)

            loaded_store = CredentialsStore.load(file_path=file_path)
            self.assertEqual(loaded_store.get_stored_key("openai"), "sk-123456789")

    def test_get_key_env_var_priority(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "credentials.json"
            store = CredentialsStore(keys={"anthropic": "stored-key"})
            store.save(file_path=file_path)

            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
                loaded_store = CredentialsStore.load(file_path=file_path)
                self.assertEqual(loaded_store.get_key("anthropic"), "env-key")

    def test_get_key_fallback_to_stored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "credentials.json"
            store = CredentialsStore(keys={"anthropic": "stored-key"})
            store.save(file_path=file_path)

            with patch.dict(os.environ, {}, clear=True):
                loaded_store = CredentialsStore.load(file_path=file_path)
                self.assertEqual(loaded_store.get_key("anthropic"), "stored-key")

    def test_set_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "credentials.json"
            store = CredentialsStore()
            store.set_key("mistral", "mistral-secret-key", file_path=file_path)

            loaded_store = CredentialsStore.load(file_path=file_path)
            self.assertEqual(loaded_store.get_stored_key("mistral"), "mistral-secret-key")


if __name__ == "__main__":
    unittest.main()
