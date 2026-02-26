from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.detection_service import get_detection_service

AUTO_TAG_SUPPORTED = {"garbage", "pothole"}
VISUAL_VALIDATION_CATEGORIES = {"garbage", "waste", "pothole", "road"}


def _normalize_category(value: str | None) -> str:
    return str(value or "").strip().lower()


def _select_auto_category(detections: list[dict[str, Any]]) -> str | None:
    if not detections:
        return None
    best = max(detections, key=lambda row: float(row.get("confidence", 0.0)))
    best_class = _normalize_category(best.get("class"))
    best_conf = float(best.get("confidence", 0.0))
    if best_class in AUTO_TAG_SUPPORTED and best_conf >= settings.detection_autotag_threshold:
        return best_class
    return None


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
