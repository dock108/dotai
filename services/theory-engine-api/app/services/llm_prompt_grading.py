"""LLM prompt grading for betting theories."""

from __future__ import annotations

import os
from typing import Any
from openai import OpenAI

from ..logging_config import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are the dock108 theory prompt grader.
Given a sports betting theory, return a JSON object with:
- grade: A-F for testability/clarity
- suggestions: 3 short bullets on how to make it more specific and testable
Be concise and specific. Only return JSON.
""".strip()


def grade_prompt(theory_text: str, sport: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for prompt grading")

    client = OpenAI(api_key=api_key, timeout=60.0)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))

    user_prompt = f"Sport: {sport}\nTheory:\n\"\"\"{theory_text}\"\"\"\nReturn JSON with grade and suggestions."

    logger.info("calling_prompt_grader", model=model, prompt_len=len(user_prompt))

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
        raise ValueError("Empty prompt grading response")
    return response.choices[0].message.parsed or {}

