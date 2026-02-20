from __future__ import annotations


def classify_image_issue(image_url: str) -> dict:
    return {
        "image_url": image_url,
        "predicted_category": "unknown",
        "confidence": 0.0,
    }