"""LLM summary generation for theory run results."""

from __future__ import annotations

import os
from typing import Any
from openai import OpenAI

from ..logging_config import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are the dock108 Theory Bets summarizer.
Given model results and the original theory, produce:
- summary: short hero copy
- stat_drivers: list of {name, importance_score}
- model_explanation: 2-3 sentences in plain language
- prompt_feedback: 3 bullets to improve the next theory
Return JSON only with those fields.
""".strip()


def generate_summary(model_results: dict[str, Any], theory_text: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for summary generation")

    client = OpenAI(api_key=api_key, timeout=60.0)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

    user_prompt = (
        "Original theory:\n"
        f"\"\"\"{theory_text}\"\"\"\n\n"
        "Model results (JSON):\n"
        f"{model_results}\n\n"
        "Return JSON with keys: summary, stat_drivers, model_explanation, prompt_feedback."
    )

    logger.info("calling_summary_llm", model=model, prompt_len=len(user_prompt))

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
        raise ValueError("Empty summary response")
    return response.choices[0].message.parsed or {}

