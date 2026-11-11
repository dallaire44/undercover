"""The model the agents run on, and the middleware that keeps them going."""

import os

from dotenv import load_dotenv
from langchain.agents.middleware import ModelCallLimitMiddleware, ModelRetryMiddleware
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"
TIMEOUT_SECONDS = 120
CLAIM_MODEL_CALLS = 30
QUEUE_RETRIES = 5
RETRY_DELAY_SECONDS = 2.0


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or DeepSeek V4.1 Flash by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )


def claim_middleware() -> list:
    """Retry failed model calls, then give up; stop a claim that loops."""
    return [
        ModelRetryMiddleware(
            max_retries=2, initial_delay=RETRY_DELAY_SECONDS, on_failure="error"
        ),
        ModelCallLimitMiddleware(run_limit=CLAIM_MODEL_CALLS, exit_behavior="error"),
    ]


def queue_middleware() -> list:
    """Retry failed model calls more often, since a failure here stops the run."""
    return [
        ModelRetryMiddleware(
            max_retries=QUEUE_RETRIES,
            initial_delay=RETRY_DELAY_SECONDS,
            on_failure="error",
        )
    ]
