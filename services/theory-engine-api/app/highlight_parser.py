"""AI-powered parser for converting user text into structured highlight request specs."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from openai import OpenAI

from py_core.schemas.highlight_request import HighlightRequestParseResult, HighlightRequestSpec


def calculate_default_duration(parsed_data: dict[str, Any]) -> int:
    """Calculate default duration based on date range scope.
    
    Rules:
    - If user specified duration, use it (handled elsewhere)
    - If date range exists, calculate based on scope:
      - Single date: 60-90 minutes
      - Week range: 90-180 minutes
      - Month range: 180-360 minutes
      - Season/Year range: 360-480 minutes
      - Decade range: 480-600 minutes (10 hours)
    - If no date range: default to 60-120 minutes (randomly pick 60, 90, or 120)
    
    Args:
        parsed_data: Parsed data dict from AI
    
    Returns:
        Default duration in minutes (60-600)
    """
    import random
    from datetime import datetime
    
    date_range = parsed_data.get("date_range")
    
    # If no date range, default to 60-120 minutes
    if not date_range or (not date_range.get("start_date") and not date_range.get("end_date") and 
                          not date_range.get("single_date") and not date_range.get("week") and 
                          not date_range.get("season")):
        # Randomly pick 60, 90, or 120 minutes
        return random.choice([60, 90, 120])
    
    # Calculate scope based on date range
    start_date = date_range.get("start_date")
    end_date = date_range.get("end_date")
    single_date = date_range.get("single_date")
    week = date_range.get("week")
    season = date_range.get("season")
    
    # Single date
    if single_date:
        return random.choice([60, 75, 90])  # 60-90 minutes
    
    # Week reference
    if week:
        return random.choice([90, 120, 150, 180])  # 90-180 minutes
    
    # Season/Year reference
    if season:
        # Check if it's a decade (e.g., "1990s" or year range spanning 8+ years)
        if isinstance(season, str) and season.endswith("s"):
            # Decade range
            return random.choice([480, 540, 600])  # 8-10 hours
        else:
            # Single year or season
            return random.choice([360, 420, 480])  # 6-8 hours
    
    # Date range
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            
            days_diff = (end_dt - start_dt).days if hasattr(end_dt, '__sub__') else 0
            
            # Single day
            if days_diff == 0:
                return random.choice([60, 75, 90])  # 60-90 minutes
            # Week range (1-7 days)
            elif days_diff <= 7:
                return random.choice([90, 120, 150, 180])  # 90-180 minutes
            # Month range (8-60 days)
            elif days_diff <= 60:
                return random.choice([180, 240, 300, 360])  # 3-6 hours
            # Season range (61-180 days)
            elif days_diff <= 180:
                return random.choice([360, 420, 480])  # 6-8 hours
            # Year+ range (181+ days) or decade
            else:
                # Check if it's a decade (8-12 years)
                if days_diff >= 2920 and days_diff <= 4380:  # ~8-12 years
                    return random.choice([480, 540, 600])  # 8-10 hours
                else:
                    return random.choice([360, 420, 480])  # 6-8 hours
        except (ValueError, TypeError, AttributeError):
            # If date parsing fails, default to 60-120 minutes
            return random.choice([60, 90, 120])
    
    # Fallback: no date range detected
    return random.choice([60, 90, 120])


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
    
    # Get current date for context
    from datetime import timedelta
    from ..utils import now_utc
    now = now_utc()
    current_date_str = now.strftime("%Y-%m-%d")
    current_year = now.year
    current_month = now.month
    current_day = now.day
    
    # Calculate "this week" boundaries (Monday to Sunday)
    days_since_monday = now.weekday()
    week_start = now - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    this_week_start = week_start.strftime("%Y-%m-%d")
    this_week_end = week_end.strftime("%Y-%m-%d")
    
    # Add date context to the prompt
    date_context = f"\n\nCURRENT DATE CONTEXT:\n- Today's date: {current_date_str}\n- Current year: {current_year}\n- This week: {this_week_start} to {this_week_end}\n- When parsing relative dates like 'this week', 'last week', 'yesterday', 'today', use these dates as reference.\n"
    
    # Call OpenAI with structured output
    try:
        # Request JSON output
        enhanced_prompt = f"{system_prompt}{date_context}\n\nIMPORTANT: Return ONLY valid JSON, no markdown, no explanations."
        
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
        
        # Calculate default duration if not specified
        if "requested_duration_minutes" not in parsed_data or parsed_data["requested_duration_minutes"] is None:
            parsed_data["requested_duration_minutes"] = calculate_default_duration(parsed_data)
        
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

