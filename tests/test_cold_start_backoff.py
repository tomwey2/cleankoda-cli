import asyncio
import unittest
from unittest.mock import MagicMock, patch

from litellm.exceptions import (
    APIConnectionError,
    APIError,
    ServiceUnavailableError,
)

from cleankoda.llm.service import is_cold_start_error, stream_chat_response
from cleankoda.session_state import SessionState


class TestColdStartBackoff(unittest.TestCase):

    def test_is_cold_start_error_detection(self):
        err_503 = ServiceUnavailableError(
            message="503 Service Unavailable",
            response=MagicMock(status_code=503),
            llm_provider="custom",
            model="qwen",
        )
        self.assertTrue(is_cold_start_error(err_503))

        err_loading = APIConnectionError(
            message="OpenAIException - Loading model",
            llm_provider="custom",
            model="qwen",
        )
        self.assertTrue(is_cold_start_error(err_loading))

        err_other = APIError(
            message="Invalid arguments",
            llm_provider="custom",
            model="qwen",
            status_code=400,
        )
        self.assertFalse(is_cold_start_error(err_other))

    def test_exponential_backoff_retry_success(self):
        async def _test():
            state = SessionState(provider="custom", model="qwen")
            messages = [{"role": "user", "content": "Hello"}]

            call_count = 0
            delays_recorded = []

            async def mock_acompletion(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise ServiceUnavailableError(
                        message="503 Service Unavailable: Loading model",
                        response=MagicMock(status_code=503),
                        llm_provider="custom",
                        model="qwen",
                    )
                mock_chunk = {
                    "id": "chatcmpl-test",
                    "object": "chat.completion.chunk",
                    "created": 12345,
                    "model": "qwen",
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant", "content": "Model ready content"},
                        "finish_reason": "stop"
                    }]
                }
                yield mock_chunk

            async def mock_wait_for(fut, timeout):
                delays_recorded.append(timeout)
                raise asyncio.TimeoutError()

            cancel_event = asyncio.Event()
            with patch("litellm.acompletion", side_effect=mock_acompletion), patch(
                "asyncio.wait_for", side_effect=mock_wait_for
            ):
                chunks = []
                async for token in stream_chat_response(
                    messages, state, cancel_event=cancel_event, initial_delay=10.0, max_attempts=10
                ):
                    chunks.append(token)

                output = "".join(chunks)
                self.assertEqual(call_count, 3)
                self.assertEqual(delays_recorded, [10.0, 20.0])
                self.assertIn("Versuch 1/10", output)
                self.assertIn("Versuch 2/10", output)
                self.assertIn("Modell bereit", output)
                self.assertIn("Model ready content", output)

        asyncio.run(_test())

    def test_escape_cancellation(self):
        async def _test():
            state = SessionState(provider="custom", model="qwen")
            messages = [{"role": "user", "content": "Hello"}]
            cancel_event = asyncio.Event()

            async def mock_acompletion(*args, **kwargs):
                raise ServiceUnavailableError(
                    message="Loading model",
                    response=MagicMock(status_code=503),
                    llm_provider="custom",
                    model="qwen",
                )

            async def mock_wait_for(fut, timeout):
                cancel_event.set()
                await fut
                return True

            with patch("litellm.acompletion", side_effect=mock_acompletion), patch(
                "asyncio.wait_for", side_effect=mock_wait_for
            ):
                chunks = []
                async for token in stream_chat_response(
                    messages, state, cancel_event=cancel_event, initial_delay=10.0, max_attempts=10
                ):
                    chunks.append(token)

                output = "".join(chunks)
                self.assertIn("Versuch 1/10", output)
                self.assertIn("Start des LLMs abgebrochen.", output)

        asyncio.run(_test())

    def test_max_attempts_exceeded(self):
        async def _test():
            state = SessionState(provider="custom", model="qwen")
            messages = [{"role": "user", "content": "Hello"}]

            call_count = 0

            async def mock_acompletion(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                raise ServiceUnavailableError(
                    message="503 Service Unavailable: Loading model",
                    response=MagicMock(status_code=503),
                    llm_provider="custom",
                    model="qwen",
                )

            async def mock_wait_for(fut, timeout):
                raise asyncio.TimeoutError()

            with patch("litellm.acompletion", side_effect=mock_acompletion), patch(
                "asyncio.wait_for", side_effect=mock_wait_for
            ):
                chunks = []
                async for token in stream_chat_response(
                    messages, state, initial_delay=1.0, max_attempts=3
                ):
                    chunks.append(token)

                output = "".join(chunks)
                self.assertEqual(call_count, 4)
                self.assertIn("Serverless LLM konnte nach 3 Versuchen nicht gestartet werden.", output)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
