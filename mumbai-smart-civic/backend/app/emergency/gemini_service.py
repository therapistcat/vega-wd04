"""
Gemini 2.5 Flash service for emergency context extraction and step generation.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

LOGGER = logging.getLogger(__name__)

GEMINI_API_KEY = "AIzaSyCXklmVrCcX15UpTvbAMIrjxeUq6bZh_0A"
GEMINI_MODEL   = "models/gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Prompt: extract disaster context
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are an emergency dispatcher AI. Analyze the user's emergency description and extract structured information.

User input: "{user_input}"

Return ONLY a valid JSON object with these exact fields:
{{
  "disaster_type": "<one of: earthquake, fire, flood, medical, accident, generic>",
  "location_context": "<brief location description, e.g. 'home kitchen', 'school 3rd floor', 'office basement', or null>",
  "floor_level": <integer floor number or null>,
  "urgency_level": "<one of: critical, high, medium, low>"
}}

Rules:
- disaster_type must be EXACTLY one of: earthquake, fire, flood, medical, accident, generic
- location_context should capture WHERE the person is (home, school, office, hospital, market, etc.) and any floor/room detail
- Return ONLY the JSON, no extra text
"""

# ---------------------------------------------------------------------------
# Prompt: generate 3 personalized step descriptions
# ---------------------------------------------------------------------------
STEPS_PROMPT = """You are an emergency safety advisor. The person is experiencing a {disaster_type} emergency.
Location: {location_context}
Key actions they must take: {actions_list}

Write EXACTLY 3 short, clear, actionable safety instructions personalized to their location and situation.
Each instruction should be 1-2 sentences max, written in simple language (imagine the person is panicking).
Mention their specific location when helpful (e.g. "Since you are in the kitchen...").

Return ONLY a JSON array of exactly 3 strings:
["instruction 1", "instruction 2", "instruction 3"]

No extra text, no markdown, just the JSON array.
"""

# ---------------------------------------------------------------------------
# Extraction implementation
# ---------------------------------------------------------------------------
async def extract_emergency_context(user_input: str) -> dict[str, Any]:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = EXTRACTION_PROMPT.format(user_input=user_input[:800])
    response = await _async_generate(model, prompt)
    raw_text = response.text.strip()

    raw_text = _strip_markdown_fence(raw_text)
    parsed = json.loads(raw_text)

    return {
        "disaster_type":    _validate_disaster_type(parsed.get("disaster_type")),
        "location_context": parsed.get("location_context"),
        "floor_level":      parsed.get("floor_level"),
        "urgency_level":    _validate_urgency(parsed.get("urgency_level")),
    }


# ---------------------------------------------------------------------------
# Step description generation
# ---------------------------------------------------------------------------
async def generate_step_descriptions(
    disaster_type: str,
    location_context: str | None,
    actions: list[str],
) -> list[str]:
    from app.emergency.assets import ACTION_LABELS, DISASTER_TITLES

    loc = location_context or "an unspecified location"
    actions_text = ", ".join(
        ACTION_LABELS.get(a, a.replace("_", " ")) for a in actions[:6]
    )

    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = STEPS_PROMPT.format(
        disaster_type=DISASTER_TITLES.get(disaster_type, disaster_type).title(),
        location_context=loc,
        actions_list=actions_text,
    )
    response = await _async_generate(model, prompt)
    raw_text = _strip_markdown_fence(response.text.strip())
    parsed = json.loads(raw_text)

    if isinstance(parsed, list) and len(parsed) >= 3:
        return [str(s) for s in parsed[:3]]
    else:
        raise ValueError("Invalid format from Gemini step generation")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_VALID_DISASTER_TYPES = {"earthquake", "fire", "flood", "medical", "accident", "generic"}
_VALID_URGENCY        = {"critical", "high", "medium", "low"}


def _validate_disaster_type(value: Any) -> str:
    v = str(value or "generic").lower().strip()
    return v if v in _VALID_DISASTER_TYPES else "generic"


def _validate_urgency(value: Any) -> str:
    v = str(value or "high").lower().strip()
    return v if v in _VALID_URGENCY else "high"


def _strip_markdown_fence(text: str) -> str:
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = text.rstrip("`").strip()
    return text


async def _async_generate(model: Any, prompt: str) -> Any:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: model.generate_content(prompt),
    )
