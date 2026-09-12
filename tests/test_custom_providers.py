import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cleankoda.commands import CommandContext
from cleankoda.commands.cmd_provider import cmd_provider
from cleankoda.config import AppConfig, config
from cleankoda.llm.config import (
    ProviderConfig,
    get_available_providers,
    get_models_for_provider,
    get_provider_config,
    get_provider_configs,
    load_provider_registry,
)
from cleankoda.llm.service import LLMService


class TestCustomProviders(unittest.TestCase):

    def test_load_custom_json_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom.json"
            content = {
                "gcp_serverless": {
                    "name": "GCP Private LLM",
                    "api_base": "https://my-llm-service-xyz.a.run.app/v1",
                    "models": ["qwen2.5-coder:32b", "mistral-large"],
                    "requires_api_key": True,
                },
                "ollama": {
                    "name": "Ollama Custom",
                    "api_base": "http://localhost:11434/v1",
                    "models": ["custom-model:7b"],
                    "requires_api_key": False,
                },
            }
            with open(custom_path, "w", encoding="utf-8") as f:
                json.dump(content, f)

            registry = load_provider_registry(custom_file_path=custom_path)
            self.assertIn("gcp_serverless", registry)
            self.assertIn("ollama", registry)

            gcp_cfg = registry["gcp_serverless"]
            self.assertEqual(gcp_cfg.name, "GCP Private LLM")
            self.assertEqual(gcp_cfg.api_base, "https://my-llm-service-xyz.a.run.app/v1")
            self.assertTrue(gcp_cfg.is_custom)
            self.assertEqual(gcp_cfg.models, ["qwen2.5-coder:32b", "mistral-large"])

            ollama_cfg = registry["ollama"]
            self.assertEqual(ollama_cfg.name, "Ollama Custom")
            self.assertEqual(ollama_cfg.models, ["custom-model:7b"])

            models = get_models_for_provider("gcp_serverless", custom_file_path=custom_path)
            self.assertEqual(models, ["qwen2.5-coder:32b", "mistral-large"])

    def test_load_custom_json_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "non_existent.json"
            registry = load_provider_registry(custom_file_path=custom_path)
            self.assertIn("mistral", registry)
            self.assertNotIn("gcp_serverless", registry)

    def test_load_custom_json_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom.json"
            with open(custom_path, "w", encoding="utf-8") as f:
                f.write("{ invalid json ... ")

            registry = load_provider_registry(custom_file_path=custom_path)
            self.assertIn("openai", registry)
            self.assertNotIn("invalid", registry)

    def test_litellm_model_identifier_custom_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom.json"
            content = {
                "gcp_serverless": {
                    "name": "GCP Private LLM",
                    "api_base": "https://my-llm-service-xyz.a.run.app/v1",
                    "models": ["qwen2.5-coder:32b"],
                }
            }
            with open(custom_path, "w", encoding="utf-8") as f:
                json.dump(content, f)

            with patch("cleankoda.llm.config.CUSTOM_CONFIG_FILE", custom_path):
                cfg = AppConfig(provider="gcp_serverless", model="qwen2.5-coder:32b")
                self.assertEqual(cfg.litellm_model_identifier, "openai/qwen2.5-coder:32b")

    def test_stream_chat_response_custom_provider(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmpdir:
                custom_path = Path(tmpdir) / "custom.json"
                content = {
                    "vllm": {
                        "name": "vLLM Local",
                        "api_base": "http://localhost:8000/v1",
                        "models": ["meta-llama/Llama-3-8b"],
                    }
                }
                with open(custom_path, "w", encoding="utf-8") as f:
                    json.dump(content, f)

                with patch("cleankoda.llm.config.CUSTOM_CONFIG_FILE", custom_path), patch.object(
                    config, "provider", "vllm"
                ), patch.object(config, "model", "meta-llama/Llama-3-8b"):
                    messages = [{"role": "user", "content": "Hello vLLM"}]

                    async def mock_acompletion(*args, **kwargs):
                        self.assertEqual(kwargs.get("api_base"), "http://localhost:8000/v1")
                        self.assertEqual(kwargs.get("api_key"), "dummy")
                        self.assertEqual(kwargs.get("model"), "openai/meta-llama/Llama-3-8b")
                        mock_chunk = {
                            "choices": [{"delta": {"content": "Hello back"}}]
                        }
                        yield mock_chunk

                    with patch("litellm.acompletion", side_effect=mock_acompletion):
                        chunks = []
                        async for token in LLMService().stream_completion(messages, tools=[]):
                            chunks.append(token)

                        self.assertEqual("".join(chunks), "Hello back")

        asyncio.run(_test())

    def test_cmd_provider_custom_provider(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmpdir:
                custom_path = Path(tmpdir) / "custom.json"
                cred_path = Path(tmpdir) / "credentials.json"
                config_path = Path(tmpdir) / "config.json"

                content = {
                    "my_custom": {
                        "name": "My Custom Provider",
                        "api_base": "https://custom.endpoint/v1",
                        "models": ["my-model-1"],
                        "requires_api_key": True,
                    }
                }
                with open(custom_path, "w", encoding="utf-8") as f:
                    json.dump(content, f)

                with patch("cleankoda.llm.config.CUSTOM_CONFIG_FILE", custom_path), patch(
                    "cleankoda.llm.credentials.DEFAULT_CREDENTIALS_FILE", cred_path
                ):
                    ctx = CommandContext(memory=MagicMock())
                    with patch(
                        "cleankoda.commands.cmd_provider.prompt_for_api_key_interactive",
                        return_value="secret-custom-key",
                    ):
                        res = await cmd_provider(["my_custom"], ctx)
                        self.assertIn("API key updated. Provider switched to: my_custom", res.output)

                        loaded_config = AppConfig.load()
                        self.assertEqual(loaded_config.provider, "my_custom")

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
