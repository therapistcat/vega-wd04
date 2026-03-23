from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.blockchain.ledger_service import log_complaint_created
from app.models.complaint_model import COMPLAINTS_COLLECTION, build_complaint_document
from app.services.clustering_service import process_issue as cluster_process_issue
from app.services.complaint_service import enrich_complaint_with_detection
from app.services.duplicate_service import resolve_duplicate_group
from app.services.geo_service import run_st_dbscan_clustering, update_intensity_scores
from app.services.ml_service import compute_priority_score, predict_department


DEFAULT_CITY_COORDS = (19.0760, 72.8777)


async def create_ingested_complaint(
    db: AsyncIOMotorDatabase,
    *,
    description: str,
    category: str,
    ward: str,
    background_tasks: BackgroundTasks | None = None,
    reporter_name: str | None = None,
    landmark: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    image_url: str | None = None,
    user_id: str | None = None,
    source: str = "web",
    call_metadata: dict[str, Any] | None = None,
    extra_fields: dict[str, Any] | None = None,
    cluster_location: str | None = None,
    actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_lat = float(lat) if lat is not None else DEFAULT_CITY_COORDS[0]
    resolved_lng = float(lng) if lng is not None else DEFAULT_CITY_COORDS[1]

    detection_enrichment = None
    final_category = category
    if image_url:
        detection_enrichment = await enrich_complaint_with_detection(
            image_url=image_url,
            user_category=category,
        )
        if detection_enrichment.get("should_reject"):
            raise HTTPException(status_code=400, detail=str(detection_enrichment.get("reject_reason") or "Invalid complaint image"))
        final_category = str(detection_enrichment["final_category"])

    department = await predict_department(description, final_category)
    duplicate_group = await resolve_duplicate_group(
        db,
        lng=resolved_lng,
        lat=resolved_lat,
    )

    complaint_doc = build_complaint_document(
        user_id=user_id,
        description=description,
        category=final_category,
        ward=ward,
        lng=resolved_lng,
        lat=resolved_lat,
        priority_score=compute_priority_score(final_category),
        predicted_department=department,
        duplicate_group=duplicate_group,
        image_url=image_url,
        source=source,
        call_metadata=call_metadata,
    )

    if detection_enrichment is not None:
        complaint_doc["category_source"] = detection_enrichment["category_source"]
        complaint_doc["vision_detection"] = detection_enrichment["vision_detection"]

    if reporter_name:
        complaint_doc["reported_by_name"] = str(reporter_name).strip()
    if landmark:
        complaint_doc["landmark"] = str(landmark).strip()
    if extra_fields:
        complaint_doc.update(extra_fields)

    insert_result = await db[COMPLAINTS_COLLECTION].insert_one(complaint_doc)
    complaint_id = str(insert_result.inserted_id)
    inserted = await db[COMPLAINTS_COLLECTION].find_one({"_id": insert_result.inserted_id})
    if not inserted:
        raise HTTPException(status_code=500, detail="Failed to fetch inserted complaint")

    try:
        cluster_result = await cluster_process_issue(
            db,
            category=final_category,
            location=cluster_location or landmark or ward,
            description=description,
            complaint_id=complaint_id,
            user_id=user_id,
            source=source,
        )
        await db[COMPLAINTS_COLLECTION].update_one(
            {"_id": insert_result.inserted_id},
            {
                "$set": {
                    "cluster_id": cluster_result["cluster_id"],
                    "is_duplicate": cluster_result["is_duplicate"],
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        inserted["cluster_id"] = cluster_result["cluster_id"]
        inserted["is_duplicate"] = cluster_result["is_duplicate"]
    except Exception as exc:
        print(f"[complaint-ingestion] clustering error: {exc}")

    if background_tasks is not None:
        background_tasks.add_task(run_st_dbscan_clustering, db)
        background_tasks.add_task(update_intensity_scores, db)

    await log_complaint_created(
        db,
        issue=inserted,
        actor=actor or {"id": user_id or "", "name": reporter_name or source.title(), "role": "citizen"},
    )

    return inserted
