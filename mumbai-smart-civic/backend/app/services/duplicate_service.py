from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.models.complaint_model import COMPLAINTS_COLLECTION


async def resolve_duplicate_group(
    db: AsyncIOMotorDatabase,
    *,
    lng: float,
    lat: float,
    now: datetime | None = None,
) -> str | None:
    current_time = now or datetime.now(timezone.utc)
    window_start = current_time - timedelta(hours=settings.duplicate_window_hours)

    query: dict[str, Any] = {
        "created_at": {"$gte": window_start},
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": settings.duplicate_radius_meters,
            }
        },
    }

    existing = await db[COMPLAINTS_COLLECTION].find_one(query, sort=[("created_at", -1)])
    if not existing:
        return None

    if existing.get("duplicate_group"):
        return str(existing["duplicate_group"])
    return str(existing["_id"])