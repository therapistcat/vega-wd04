from __future__ import annotations

from typing import Any


SUPPORTED_CLASSES = {"garbage", "pothole"}


def summarize_detections(detections: list[dict[str, Any]]) -> dict[str, Any]:
    if not detections:
        return {
            "top_class": None,
            "top_confidence": 0.0,
            "class_counts": {},
        }

    class_counts: dict[str, int] = {}
    top = max(detections, key=lambda d: float(d.get("confidence", 0.0)))
    for row in detections:
        cls = str(row.get("class", "")).strip().lower()
        if not cls:
            continue
        class_counts[cls] = class_counts.get(cls, 0) + 1

    return {
        "top_class": str(top.get("class", "")).lower() or None,
        "top_confidence": float(top.get("confidence", 0.0)),
        "class_counts": class_counts,
    }

