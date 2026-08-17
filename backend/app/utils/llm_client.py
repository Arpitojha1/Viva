"""
Viva — Groq LLM Client (via OpenAI SDK)
Wraps the OpenAI async client pointed at Groq's endpoint.
Includes retry logic with exponential backoff for rate limit errors (429).
"""
import asyncio
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI, RateLimitError, APIStatusError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def get_groq_client() -> AsyncOpenAI:
    """Return a cached AsyncOpenAI client pointed at Groq's API endpoint."""
    return AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        timeout=30.0,
    )


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(4),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_format: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Call Groq's chat completion API.

    Args:
        messages: List of {role, content} dicts.
        model: Override the default generation model. Pass settings.groq_model_scoring
               for lightweight scoring calls.
        temperature: Sampling temperature.
        max_tokens: Max tokens in the response.
        response_format: Optional {"type": "json_object"} for structured output.

    Returns:
        The assistant message content as a string.

    Raises:
        RateLimitError: After 4 retries with exponential backoff.
        APIStatusError: For non-retriable API errors.
    """
    client = get_groq_client()
    chosen_model = model or settings.groq_model_generation

    kwargs: Dict[str, Any] = {
        "model": chosen_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    logger.debug("Groq chat_completion | model=%s | messages=%d", chosen_model, len(messages))

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=35.0  # Slightly higher than client timeout
        )
    except asyncio.TimeoutError as exc:
        logger.error("Groq API timed out after 35s")
        raise APIStatusError(
            message="Groq API timeout",
            response=None,
            body=None
        ) from exc

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Groq returned an empty response content")
    return content
