from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.complaint_model import COMPLAINTS_COLLECTION


async def compute_spatial_analytics(
    db: AsyncIOMotorDatabase,
    *,
    lat: float | None = None,
    lng: float | None = None,
    radius_m: int | None = None,
    window_hours: int = 168,
) -> list[dict[str, float]]:
    match_query: dict[str, Any] = {}
    if window_hours > 0:
        match_query["created_at"] = {
            "$gte": datetime.now(timezone.utc) - timedelta(hours=window_hours)
        }

    pipeline: list[dict[str, Any]] = []

    if lat is not None and lng is not None:
        geo_near: dict[str, Any] = {
            "near": {"type": "Point", "coordinates": [lng, lat]},
            "distanceField": "distance_m",
            "spherical": True,
            "query": match_query,
        }
        if radius_m is not None and radius_m > 0:
            geo_near["maxDistance"] = radius_m
        pipeline.append({"$geoNear": geo_near})
    elif match_query:
        pipeline.append({"$match": match_query})

    pipeline.extend(
        [
            {
                "$project": {
                    "lat": {"$arrayElemAt": ["$location.coordinates", 1]},
                    "lng": {"$arrayElemAt": ["$location.coordinates", 0]},
                    "priority_score": {"$ifNull": ["$priority_score", 0.5]},
                }
            },
            {
                "$addFields": {
                    "lat_bucket": {"$round": ["$lat", 4]},
                    "lng_bucket": {"$round": ["$lng", 4]},
                }
            },
            {
                "$group": {
                    "_id": {"lat": "$lat_bucket", "lng": "$lng_bucket"},
                    "complaint_count": {"$sum": 1},
                    "avg_priority": {"$avg": "$priority_score"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "lat": "$_id.lat",
                    "lng": "$_id.lng",
                    "raw_intensity": {
                        "$multiply": ["$complaint_count", "$avg_priority"]
                    },
                }
            },
            {"$sort": {"raw_intensity": -1}},
        ]
    )

    points = await db[COMPLAINTS_COLLECTION].aggregate(pipeline).to_list(length=None)
    if not points:
        return []

    max_raw = max(float(point.get("raw_intensity", 0.0)) for point in points) or 1.0
    result: list[dict[str, float]] = []

    for point in points:
        lat_value = point.get("lat")
        lng_value = point.get("lng")
        if lat_value is None or lng_value is None:
            continue

        raw = float(point.get("raw_intensity", 0.0))
        intensity = raw / max_raw
        intensity = min(1.0, max(0.0, intensity))

        result.append(
            {
                "lat": float(lat_value),
                "lng": float(lng_value),
                "intensity": round(float(intensity), 4),
            }
        )

    return result
