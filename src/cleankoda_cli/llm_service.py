import logging
from typing import AsyncGenerator, Any

import litellm
from litellm.exceptions import (
    APIError,
    AuthenticationError,
    APIConnectionError,
    RateLimitError,
    ServiceUnavailableError,
)

from cleankoda_cli.session_state import SessionState

litellm.suppress_debug_info = True


async def stream_chat_response(
    messages: list[dict[str, Any]], state: SessionState
) -> AsyncGenerator[str, None]:
    """Streamt Antworten von LiteLLM basierend auf dem angegebenen SessionState."""
    litellm.suppress_debug_info = True

    model_identifier = state.litellm_model_identifier
    api_key = state.get_active_api_key()

    kwargs: dict[str, Any] = {
        "model": model_identifier,
        "messages": messages,
        "temperature": state.temperature,
        "max_tokens": state.max_tokens,
        "stream": True,
    }

    if api_key:
        kwargs["api_key"] = api_key

    try:
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            if not chunk or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None) or ""
            if content:
                yield content

    except AuthenticationError as e:
        yield f"[Authentication Error ({state.provider}): Please check your API key. Details: {e}]"
    except RateLimitError as e:
        yield f"[Rate Limit Exceeded ({state.provider}): {e}]"
    except (APIConnectionError, ServiceUnavailableError) as e:
        yield f"[Connection Error ({state.provider}): Unable to reach server. {e}]"
    except APIError as e:
        yield f"[LLM Error ({state.provider}): {e}]"
    except Exception as e:
        yield f"[Unexpected Error ({state.provider}): {type(e).__name__} - {e}]"
