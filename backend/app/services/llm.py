"""
LLM service: the single place that talks to OpenAI's chat models.

Entity extraction and P&ID reading both go through here so client setup, model
choice, and JSON handling live in one spot instead of being copy-pasted across
the ingestion stages. Embeddings have their own module (embeddings.py).
"""

import json
import logging
from functools import lru_cache

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> OpenAI:
    """Shared OpenAI client (holds its own connection pool)."""
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def complete_json(system: str, user: str, model: str | None = None) -> dict:
    """JSON-mode completion returning just the parsed object (see _verbose for usage)."""
    data, _ = complete_json_verbose(system, user, model)
    return data


def complete_json_verbose(system: str, user: str, model: str | None = None) -> tuple[dict, dict]:
    """
    Run a chat completion in JSON mode and return (parsed object, token usage).

    JSON mode makes the model emit valid JSON, but the caller still validates the
    shape (pydantic). We log the token usage on every call so the real cost is
    visible in the backend logs, and hand it back for a debug view. Raises on a
    network error or unparseable body.
    """
    used_model = model or settings.LLM_MODEL
    resp = get_client().chat.completions.create(
        model=used_model,
        response_format={"type": "json_object"},
        temperature=0,  # extraction and grounded answers should be deterministic
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    u = resp.usage
    usage = {"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens, "total_tokens": u.total_tokens}
    logger.info("LLM %s tokens: prompt=%d completion=%d", used_model, u.prompt_tokens, u.completion_tokens)
    return json.loads(resp.choices[0].message.content), usage


def describe_image(prompt: str, image_b64: str, mime: str = "image/png", model: str | None = None) -> str:
    """Send one image plus a prompt to the vision model and return its text answer."""
    resp = get_client().chat.completions.create(
        model=model or settings.VISION_MODEL,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            }
        ],
    )
    return resp.choices[0].message.content or ""
