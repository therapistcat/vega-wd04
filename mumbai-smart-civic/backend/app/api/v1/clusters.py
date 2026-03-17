"""Cluster list and detail routes."""
from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import require_roles
from app.models.complaint_model import COMPLAINTS_COLLECTION, serialize_complaint
from app.services.clustering_service import (
    CLUSTERS_COLLECTION,
    get_cluster_with_complaints,
    list_clusters,
)

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=list[dict[str, Any]])
async def get_all_clusters(
    limit: int = 100,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[dict[str, Any]]:
    _ = current_user
    clusters = await list_clusters(db, limit=limit)
    result = []
    for c in clusters:
        result.append({
            "cluster_id": str(c.get("_id")),
            "category": c.get("category", "general"),
            "location": c.get("location", ""),
            "status": c.get("status", "Open"),
            "report_count": int(c.get("report_count") or 0),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
        })
    return result


@router.get("/{cluster_id}", response_model=dict[str, Any])
async def get_cluster_detail(
    cluster_id: str,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict[str, Any]:
    _ = current_user
    cluster = await get_cluster_with_complaints(db, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Fetch linked complaints
    report_ids = []
    for r in cluster.get("reports", []):
        cid = r.get("complaint_id")
        if cid:
            try:
                report_ids.append(ObjectId(cid))
            except Exception:
                pass

    linked_complaints = []
    if report_ids:
        docs = await db[COMPLAINTS_COLLECTION].find({"_id": {"$in": report_ids}}).to_list(length=len(report_ids))
        linked_complaints = [serialize_complaint(d) for d in docs]

    return {
        "cluster_id": str(cluster.get("_id")),
        "category": cluster.get("category", "general"),
        "location": cluster.get("location", ""),
        "status": cluster.get("status", "Open"),
        "report_count": int(cluster.get("report_count") or 0),
        "created_at": cluster.get("created_at"),
        "updated_at": cluster.get("updated_at"),
        "complaints": linked_complaints,
    }
