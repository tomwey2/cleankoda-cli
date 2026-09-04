import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

import litellm
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
)

from cleankoda_cli.llm_service import stream_chat_response
from cleankoda_cli.session_state import SessionState


class TestLLMService(unittest.TestCase):

    def test_stream_chat_response_success(self):
        async def _test():
            state = SessionState(provider="openai", model="gpt-4o")
            messages = [{"role": "user", "content": "Hello"}]

            mock_chunk1 = MagicMock()
            mock_chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
            mock_chunk2 = MagicMock()
            mock_chunk2.choices = [MagicMock(delta=MagicMock(content=" world!"))]

            async def mock_acompletion(*args, **kwargs):
                self.assertEqual(kwargs.get("model"), "openai/gpt-4o")
                self.assertEqual(kwargs.get("api_key"), "test-key")
                self.assertTrue(kwargs.get("stream"))
                for chunk in [mock_chunk1, mock_chunk2]:
                    yield chunk

            with patch("litellm.acompletion", side_effect=mock_acompletion), patch.object(
                SessionState, "get_active_api_key", return_value="test-key"
            ):
                chunks = []
                async for token in stream_chat_response(messages, state):
                    chunks.append(token)

                self.assertEqual("".join(chunks), "Hello world!")

        asyncio.run(_test())

    def test_stream_chat_response_ollama_no_api_key(self):
        async def _test():
            state = SessionState(provider="ollama", model="llama3.3")
            messages = [{"role": "user", "content": "Hello"}]

            async def mock_acompletion(*args, **kwargs):
                self.assertNotIn("api_key", kwargs)
                self.assertEqual(kwargs.get("model"), "ollama/llama3.3")
                mock_chunk = MagicMock()
                mock_chunk.choices = [MagicMock(delta=MagicMock(content="Ollama response"))]
                yield mock_chunk

            with patch("litellm.acompletion", side_effect=mock_acompletion):
                chunks = []
                async for token in stream_chat_response(messages, state):
                    chunks.append(token)

                self.assertEqual("".join(chunks), "Ollama response")

        asyncio.run(_test())

    def test_stream_chat_response_auth_error(self):
        async def _test():
            state = SessionState(provider="anthropic", model="claude-3-5-sonnet-latest")
            messages = [{"role": "user", "content": "Hello"}]

            auth_err = AuthenticationError(
                message="Invalid API Key",
                response=MagicMock(status_code=401),
                llm_provider="anthropic",
                model="claude-3-5-sonnet-latest",
            )

            with patch("litellm.acompletion", side_effect=auth_err):
                chunks = []
                async for token in stream_chat_response(messages, state):
                    chunks.append(token)

                result = "".join(chunks)
                self.assertIn("Authentication Error", result)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
