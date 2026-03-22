from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.core.config import settings
from app.models.complaint_model import COMPLAINTS_COLLECTION
from ml_engine.cluster import st_dbscan_cluster


async def run_st_dbscan_clustering(db: AsyncIOMotorDatabase) -> None:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    cursor = db[COMPLAINTS_COLLECTION].find(
        {"created_at": {"$gte": start}, "status": {"$ne": "Resolved"}},
        {
            "_id": 1,
            "location": 1,
            "created_at": 1,
            "duplicate_group": 1,
        },
    )
    docs = await cursor.to_list(length=None)
    if not docs:
        return

    assignments = st_dbscan_cluster(
        docs,
        spatial_eps_meters=settings.cluster_spatial_eps_meters,
        temporal_eps_hours=settings.cluster_temporal_eps_hours,
        min_samples=settings.cluster_min_samples,
    )

    ops: list[UpdateOne] = []
    for complaint_id, group_id in assignments.items():
        ops.append(
            UpdateOne(
                {"_id": ObjectId(complaint_id), "duplicate_group": None},
                {"$set": {"duplicate_group": group_id, "updated_at": now}},
            )
        )

    if ops:
        await db[COMPLAINTS_COLLECTION].bulk_write(ops, ordered=False)


async def update_intensity_scores(db: AsyncIOMotorDatabase) -> None:
    pipeline: list[dict[str, Any]] = [
        {
            "$project": {
                "lat": {"$arrayElemAt": ["$location.coordinates", 1]},
                "lng": {"$arrayElemAt": ["$location.coordinates", 0]},
                "priority_score": {"$ifNull": ["$priority_score", 0.5]},
            }
        },
        {
            "$addFields": {
                "lat_bucket": {"$round": ["$lat", 3]},
                "lng_bucket": {"$round": ["$lng", 3]},
            }
        },
        {
            "$group": {
                "_id": {"lat": "$lat_bucket", "lng": "$lng_bucket"},
                "count": {"$sum": 1},
                "avg_priority": {"$avg": "$priority_score"},
            }
        },
    ]

    grouped = await db[COMPLAINTS_COLLECTION].aggregate(pipeline).to_list(length=None)
    if not grouped:
        return

    max_raw = max(item["count"] * item["avg_priority"] for item in grouped)
    if max_raw <= 0:
        max_raw = 1.0

    ops: list[UpdateOne] = []
    for item in grouped:
        lat = item["_id"]["lat"]
        lng = item["_id"]["lng"]
        raw = item["count"] * item["avg_priority"]
        intensity = round(raw / max_raw, 4)

        ops.append(
            UpdateOne(
                {
                    "$expr": {
                        "$and": [
                            {
                                "$eq": [
                                    {"$round": [{"$arrayElemAt": ["$location.coordinates", 1]}, 3]},
                                    lat,
                                ]
                            },
                            {
                                "$eq": [
                                    {"$round": [{"$arrayElemAt": ["$location.coordinates", 0]}, 3]},
                                    lng,
                                ]
                            },
                        ]
                    }
                },
                {
                    "$set": {
                        "intensity_score": intensity,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        )

    if ops:
        await db[COMPLAINTS_COLLECTION].bulk_write(ops, ordered=False)
