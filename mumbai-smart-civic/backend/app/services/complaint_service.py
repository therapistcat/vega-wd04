from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.detection_service import get_detection_service

AUTO_TAG_SUPPORTED = {"garbage", "pothole"}
VISUAL_VALIDATION_CATEGORIES = {"garbage", "waste", "pothole", "road"}


def _normalize_category(value: str | None) -> str:
    return str(value or "").strip().lower()


def _autotag_threshold_for(class_name: str) -> float:
    normalized = _normalize_category(class_name)
    if normalized == "garbage" and settings.detection_autotag_threshold_garbage is not None:
        return float(settings.detection_autotag_threshold_garbage)
    if normalized == "pothole" and settings.detection_autotag_threshold_pothole is not None:
        return float(settings.detection_autotag_threshold_pothole)
    return float(settings.detection_autotag_threshold)


def _select_auto_category(detections: list[dict[str, Any]]) -> str | None:
    if not detections:
        return None

    eligible: list[tuple[float, str]] = []
    for row in detections:
        class_name = _normalize_category(row.get("class"))
        if class_name not in AUTO_TAG_SUPPORTED:
            continue
        confidence = float(row.get("confidence", 0.0))
        if confidence >= _autotag_threshold_for(class_name):
            eligible.append((confidence, class_name))

    if not eligible:
        return None

    eligible.sort(key=lambda item: item[0], reverse=True)
    return eligible[0][1]


async def enrich_complaint_with_detection(
    *,
    image_url: str,
    user_category: str,
) -> dict[str, Any]:
    """
    Returns category + metadata to attach to complaint doc.
    Does not raise for model-unavailable scenarios.
    """
    service = get_detection_service()
    local_path = Path(__file__).resolve().parents[1] / image_url.lstrip("/")

    detections: list[dict[str, Any]] = []
    inference_error: str | None = None

    if local_path.exists():
        try:
            detections = await service.detect_path(local_path)
        except Exception as exc:  # pragma: no cover - defensive path
            inference_error = str(exc)
    else:
        inference_error = f"Image path not found: {local_path}"

    category_norm = _normalize_category(user_category)
    auto_category = _select_auto_category(detections)
    final_category = auto_category or user_category
    category_source = "vision_auto" if auto_category else "user_input"

    reject_reason: str | None = None
    if settings.detection_strict_mode and category_norm in VISUAL_VALIDATION_CATEGORIES:
        if not service.enabled:
            reject_reason = "AI validation model is unavailable. Please try again later."
        elif auto_category is None:
            reject_reason = (
                "Uploaded image does not appear to contain a valid civic issue "
                "(garbage/pothole) with enough confidence."
            )

    return {
        "final_category": final_category,
        "category_source": category_source,
        "should_reject": reject_reason is not None,
        "reject_reason": reject_reason,
        "vision_detection": {
            "enabled": service.enabled,
            "model_path": settings.model_path,
            "auto_category": auto_category,
            "user_category": user_category,
            "detections": detections,
            "inference_error": inference_error,
        },
    }
