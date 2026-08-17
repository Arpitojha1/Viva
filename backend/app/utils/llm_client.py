"""
Viva — Groq LLM Client (via OpenAI SDK)
Wraps the OpenAI async client pointed at Groq's endpoint.
Includes retry logic with exponential backoff for rate limit errors (429).
"""
import asyncio
import logging
import json
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

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
        "max_completion_tokens": max_tokens,
    }
    if chosen_model.startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = "low"
    
    if response_format:
        kwargs["response_format"] = response_format

    logger.debug("Groq chat_completion | model=%s | messages=%d", chosen_model, len(messages))

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=120.0  # Increased timeout for complex models
        )
    except asyncio.TimeoutError as exc:
        logger.error("Groq API timed out after 120s")
        raise APIStatusError(
            message="Groq API timeout",
            response=None,
            body=None
        ) from exc

    content = response.choices[0].message.content
    if not content or not content.strip():
        finish_reason = response.choices[0].finish_reason
        raw_resp = response.model_dump_json() if hasattr(response, 'model_dump_json') else str(response)
        logger.error("Groq empty response. Finish reason: %s, Raw response: %s", finish_reason, raw_resp)
        raise ValueError(f"Groq returned an empty/whitespace response. Finish reason: {finish_reason}")
        
    return content

async def chat_completion_json(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> Union[dict, list]:
    """
    Call Groq chat completion and robustly parse the JSON response.
    Retries once with explicit JSON instructions if parsing fails.
    """
    try:
        response_text = await chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        return parse_json_response(response_text)
    except ValueError as exc:
        logger.warning("JSON parse failed, retrying once. Error: %s", exc)
        retry_messages = list(messages)
        retry_messages.append({
            "role": "user",
            "content": "Respond with ONLY the raw JSON object, no markdown fences, no explanation before or after it."
        })
        response_text = await chat_completion(
            messages=retry_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        return parse_json_response(response_text)

def parse_json_response(response: str) -> Union[dict, list]:
    """
    Robustly extract a JSON object or array from an LLM response.
    """
    # 1. Strip markdown code fences first
    fence_match = re.search(r"```(?:json)?\s*([\[\{].*?[\]\}])\s*```", response, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Try the whole response as JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 3. Extract the first {...} or [...] block
    brace_match = re.search(r"(\{.*\}|\[.*\])", response, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not extract a JSON object from LLM response "
        f"(len={len(response)}). First 200 chars: {response[:200]!r}"
    )
