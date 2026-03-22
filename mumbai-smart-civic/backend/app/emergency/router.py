"""
FastAPI router for the AI Emergency Visual Assistant.
POST /api/emergency-visual — no authentication required (emergency access).
Includes LRU caching for repeated inputs.
"""
from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.emergency.gemini_service import extract_emergency_context
from app.emergency.rule_engine import get_actions
from app.emergency.pdf_generator import generate_pdf
from app.emergency.assets import ACTION_LABELS, DISASTER_TITLES

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["emergency-visual"])

# ---------------------------------------------------------------------------
# LRU Cache (in-memory, max 50 entries)
# ---------------------------------------------------------------------------
_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()
_CACHE_MAX = 50


def _cache_get(key: str) -> dict[str, Any] | None:
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    return None


def _cache_set(key: str, value: dict[str, Any]) -> None:
    _CACHE[key] = value
    _CACHE.move_to_end(key)
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class EmergencyRequest(BaseModel):
    user_input: str = Field(min_length=2, max_length=1000)

    @field_validator("user_input")
    @classmethod
    def strip_input(cls, v: str) -> str:
        return v.strip()


class EmergencyResponse(BaseModel):
    status: str
    disaster_type: str
    disaster_title: str
    urgency_level: str
    location_context: str | None
    floor_level: int | None
    actions: list[str]
    action_labels: dict[str, str]
    pdf_url: str
    cached: bool = False


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post(
    "/api/emergency-visual",
    response_model=EmergencyResponse,
    summary="Generate AI Emergency Visual Guide",
    description=(
        "Accepts a free-form emergency description, extracts context via Gemini 2.5 Flash, "
        "applies rule-based action mapping, and generates a downloadable visual PDF guide."
    ),
)
async def generate_emergency_visual(payload: EmergencyRequest) -> EmergencyResponse:
    # --- Cache check ---
    cache_key = hashlib.sha256(payload.user_input.lower().encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached:
        LOGGER.info("Emergency cache hit for input hash %s", cache_key[:8])
        return EmergencyResponse(**cached, cached=True)

    # --- Gemini extraction ---
    try:
        context = await extract_emergency_context(payload.user_input)
    except Exception as exc:
        LOGGER.error("Emergency context extraction failed: %s", exc)
        context = {
            "disaster_type":    "generic",
            "location_context": None,
            "floor_level":      None,
            "urgency_level":    "high",
        }

    disaster_type    = context["disaster_type"]
    urgency_level    = context["urgency_level"]
    location_context = context.get("location_context")
    floor_level      = context.get("floor_level")

    # --- Rule engine ---
    actions = get_actions(disaster_type, floor_level, location_context)

    # --- PDF generation ---
    try:
        pdf_url = generate_pdf(
            disaster_type=disaster_type,
            urgency_level=urgency_level,
            actions=actions,
            location_context=location_context,
            floor_level=floor_level,
        )
    except Exception as exc:
        LOGGER.error("PDF generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation failed. Please try again.",
        ) from exc

    # Build action labels subset for response
    action_labels = {a: ACTION_LABELS.get(a, a.replace("_", " ").title()) for a in actions}

    result: dict[str, Any] = {
        "status":           "success",
        "disaster_type":    disaster_type,
        "disaster_title":   DISASTER_TITLES.get(disaster_type, "EMERGENCY"),
        "urgency_level":    urgency_level,
        "location_context": location_context,
        "floor_level":      floor_level,
        "actions":          actions,
        "action_labels":    action_labels,
        "pdf_url":          pdf_url,
    }

    _cache_set(cache_key, result)
    return EmergencyResponse(**result)
