"""
LLM service: the single place that talks to OpenAI's chat models.

Entity extraction and P&ID reading both go through here so client setup, model
choice, and JSON handling live in one spot instead of being copy-pasted across
the ingestion stages. Embeddings have their own module (embeddings.py).
"""

import json
from functools import lru_cache

from openai import OpenAI

from app.config import settings


@lru_cache
def get_client() -> OpenAI:
    """Shared OpenAI client (holds its own connection pool)."""
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def complete_json(system: str, user: str, model: str | None = None) -> dict:
    """
    Run a chat completion in JSON mode and return the parsed object.

    JSON mode makes the model emit syntactically valid JSON, but the caller is
    still responsible for validating the shape (we do that with pydantic in
    entity_extraction). Raises on a network error or unparseable body.
    """
    resp = get_client().chat.completions.create(
        model=model or settings.LLM_MODEL,
        response_format={"type": "json_object"},
        temperature=0,  # extraction should be deterministic, not creative
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(resp.choices[0].message.content)


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
