"""AI-powered parser for converting user text into structured highlight request specs."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from openai import OpenAI

from py_core.schemas.highlight_request import HighlightRequestParseResult, HighlightRequestSpec


def load_system_prompt() -> str:
    """Load the sports highlight channel system prompt.
    
    Returns:
        System prompt text
    """
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "ai_prompts",
        "sports_highlight_channel.md",
    )
    
    # Try to load from file
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # Fallback to embedded prompt (first section only)
    return """You are a planner for a sports highlight playlist generation system. 
Parse user text and output structured JSON specification. You do NOT return videos—only the spec.

Output JSON matching this structure:
{
  "sport": "NFL|NBA|MLB|NHL|NCAAF|NCAAB|PGA|F1|SOCCER|TENNIS|OTHER",
  "leagues": [],
  "teams": [],
  "date_range": {"start_date": null, "end_date": null, "single_date": null, "week": null, "season": null},
  "content_mix": {"highlights": 0.6, "bloopers": 0.0, "top_plays": 0.0, "condensed": 0.0, "full_game": 0.0, "upsets": 0.0},
  "requested_duration_minutes": 60,
  "loop_mode": "single_playlist",
  "exclusions": [],
  "nsfw_filter": true,
  "language": "en",
  "assumptions": []
}"""


async def parse_highlight_request(
    user_text: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
) -> HighlightRequestParseResult:
    """Parse user text into structured highlight request spec using AI.
    
    Args:
        user_text: Raw user input
        api_key: OpenAI API key (or from env)
        model: Model to use (default: gpt-4o-mini)
    
    Returns:
        Parse result with spec and confidence
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key required (set OPENAI_API_KEY env var)")
    
    client = OpenAI(api_key=api_key)
    system_prompt = load_system_prompt()
    
    # Call OpenAI with structured output
    try:
        # Request JSON output
        enhanced_prompt = f"{system_prompt}\n\nIMPORTANT: Return ONLY valid JSON, no markdown, no explanations."
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=0.3,  # Lower temperature for more consistent parsing
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Remove markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove closing ```
        content = content.strip()
        
        # Parse JSON response
        parsed_data = json.loads(content)
        
        # Validate and create spec
        spec = HighlightRequestSpec(**parsed_data)
        
        # Determine confidence (simple heuristic for now)
        confidence = 0.9 if not spec.assumptions else 0.7
        
        # Check if clarification needed
        needs_clarification = len(spec.assumptions) > 3 or spec.sport == "OTHER"
        clarification_questions = []
        if needs_clarification:
            if spec.sport == "OTHER":
                clarification_questions.append("Which sport are you interested in?")
            if not spec.date_range:
                clarification_questions.append("What date or date range are you looking for?")
        
        return HighlightRequestParseResult(
            spec=spec,
            confidence=confidence,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions,
        )
    
    except json.JSONDecodeError as e:
        # Fallback: try to extract JSON from response
        raise ValueError(f"Failed to parse JSON response: {e}")
    except Exception as e:
        raise ValueError(f"Failed to parse highlight request: {e}")

