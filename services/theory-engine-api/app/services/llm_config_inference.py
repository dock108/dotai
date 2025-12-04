"""LLM-based ModelConfig inference for betting theories."""

from __future__ import annotations

import os
from typing import Any
from openai import OpenAI

from ..logging_config import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are the dock108 ModelConfig builder.
Given a betting theory, infer:
- features: list of stats/features to use (strings)
- bet_types: list of bet types (e.g., spread, total, moneyline, props)
- filters: JSON object of game context filters (e.g., back_to_back, altitude, home_favorite)
Return JSON with fields: features, bet_types, filters.
Be concise and deterministic. Only return JSON.
""".strip()


def infer_model_config(theory_text: str, sport: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for config inference")

    client = OpenAI(api_key=api_key, timeout=60.0)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))

    user_prompt = f"Sport: {sport}\nTheory:\n\"\"\"{theory_text}\"\"\"\nReturn JSON with features, bet_types, filters."

    logger.info("calling_config_inference", model=model, prompt_len=len(user_prompt))

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty config inference response")
    return response.choices[0].message.parsed or {}

