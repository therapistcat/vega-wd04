from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.config import settings
from ml_engine.triage_model import predict_department as local_predict_department


async def predict_department(description: str, category: str) -> str:
    payload = {"description": description, "category": category}
    try:
        async with httpx.AsyncClient(timeout=settings.ml_service_timeout_seconds) as client:
            response = await client.post(f"{settings.ml_service_url}/triage/predict", json=payload)
            response.raise_for_status()
            data = response.json()
            department = data.get("department")
            if isinstance(department, str) and department.strip():
                return department.strip()
    except Exception:
        pass

    return local_predict_department(description=description, category=category)


def compute_priority_score(category: str, created_at: datetime | None = None) -> float:
    severity_weight = {
        "garbage": 0.75,
        "waste": 0.75,
        "pothole": 0.72,
        "water": 0.8,
        "road": 0.65,
        "electricity": 0.85,
        "sewage": 0.9,
    }
    base = severity_weight.get(category.lower(), 0.6)
    timestamp = created_at or datetime.now(timezone.utc)
    rush_hour_boost = 0.08 if timestamp.hour in {7, 8, 9, 17, 18, 19} else 0.0
    return round(min(1.0, base + rush_hour_boost), 2)
