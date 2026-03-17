"""
Gemini 2.5 Flash service for emergency context extraction.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

LOGGER = logging.getLogger(__name__)

# Updated with the new key provided by the user
GEMINI_API_KEY = "AIzaSyC1NA0bP8yZ8eI5GSC3PwhcE7C0wp_wQik"
GEMINI_MODEL   = "models/gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Extraction schema
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are an emergency dispatcher AI. Analyze the user's emergency description and extract structured information.

User input: "{user_input}"

Return ONLY a valid JSON object with these exact fields:
{{
  "disaster_type": "<one of: earthquake, fire, flood, medical, accident, generic>",
  "location_context": "<brief location description or null>",
  "floor_level": <integer floor number or null>,
  "urgency_level": "<one of: critical, high, medium, low>"
}}

Rules:
- disaster_type must be EXACTLY one of: earthquake, fire, flood, medical, accident, generic
- Return ONLY the JSON
"""

# ---------------------------------------------------------------------------
# Extraction implementation
# ---------------------------------------------------------------------------
async def extract_emergency_context(user_input: str) -> dict[str, Any]:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        prompt = EXTRACTION_PROMPT.format(user_input=user_input[:800])
        response = await _async_generate(model, prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
            raw_text = raw_text.rstrip("`").strip()

        parsed = json.loads(raw_text)
        return {
            "disaster_type":    parsed.get("disaster_type", "generic"),
            "location_context": parsed.get("location_context"),
            "floor_level":      parsed.get("floor_level"),
            "urgency_level":    parsed.get("urgency_level", "high"),
        }
    except Exception as exc:
        LOGGER.warning("Gemini extraction failed: %s", exc)
        return {"disaster_type": "generic", "location_context": None, "floor_level": None, "urgency_level": "high"}


async def _async_generate(model: Any, prompt: str) -> Any:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: model.generate_content(prompt),
    )
