from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import verify_vapi_token
from app.models.complaint_model import COMPLAINTS_COLLECTION, build_complaint_document
from app.services.call_service import parse_call_to_complaint
from app.services.clustering_service import process_issue as cluster_process_issue
from app.services.geo_service import run_st_dbscan_clustering, update_intensity_scores
from app.services.ml_service import compute_priority_score, predict_department

router = APIRouter(prefix="/vapi", tags=["vapi"])


def _nested_get(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_call_id(body: dict[str, Any]) -> str | None:
    candidates = [
        _nested_get(body, "call", "id"),
        _nested_get(body, "message", "call", "id"),
        _nested_get(body, "message", "callId"),
        body.get("callId"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_event_type(body: dict[str, Any]) -> str:
    candidates = [
        body.get("type"),
        _nested_get(body, "message", "type"),
        _nested_get(body, "message", "eventType"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return "unknown"


def _extract_summary(body: dict[str, Any]) -> str | None:
    candidates = [
        _nested_get(body, "message", "analysis", "summary"),
        _nested_get(body, "analysis", "summary"),
        body.get("summary"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_transcript(body: dict[str, Any]) -> str | None:
    candidates = [
        body.get("transcript"),
        _nested_get(body, "message", "transcript"),
        _nested_get(body, "message", "artifact", "transcript"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


@router.get("/ping")
async def vapi_ping(_: bool = Depends(verify_vapi_token)) -> dict[str, Any]:
    return {"ok": True, "service": "vapi", "authenticated": True}


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_vapi_token),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    call_id = _extract_call_id(body)
    event_type = _extract_event_type(body)
    transcript = _extract_transcript(body)
    summary = _extract_summary(body)

    event_doc = {
        "receivedAt": datetime.now(timezone.utc),
        "callId": call_id,
        "type": event_type,
        "payload": body,
    }
    await db["vapi_events"].insert_one(event_doc)

    complaint_created = False
    complaint_id: str | None = None

    try:
        if event_type == "end-of-call-report" and call_id:
            existing = await db[COMPLAINTS_COLLECTION].find_one(
                {"call_metadata.call_id": call_id},
                {"_id": 1},
            )
            if existing:
                complaint_id = str(existing["_id"])
            else:
                raw_call_text = (summary or transcript or "").strip()
                if raw_call_text:
                    parsed = parse_call_to_complaint(summary or "", transcript=transcript)
                    complaint_text = parsed.get("description") or parsed.get("summary") or ""
                    department = await predict_department(
                        complaint_text,
                        parsed["category"],
                    )
                    phone_number = (
                        _nested_get(body, "call", "customer", "number")
                        or _nested_get(body, "message", "call", "customer", "number")
                        or "unknown"
                    )
                    duration = (
                        _nested_get(body, "call", "duration")
                        or _nested_get(body, "message", "call", "duration")
                    )

                    complaint_doc = build_complaint_document(
                        user_id=None,
                        description=complaint_text,
                        category=parsed["category"],
                        ward=parsed["ward"],
                        priority_score=compute_priority_score(parsed["category"]),
                        predicted_department=department,
                        source="call",
                        call_metadata={
                            "call_id": call_id,
                            "event_type": event_type,
                            "phone_number": phone_number,
                            "duration": duration,
                            "summary": parsed.get("summary"),
                            "problem": parsed.get("problem"),
                            "location_text": parsed.get("location"),
                            "details": parsed.get("details"),
                            "transcript": transcript,
                        },
                    )
                    complaint_doc["reported_by_name"] = "Voice Hotline"
                    complaint_doc["title"] = parsed["title"]
                    complaint_doc["is_verified"] = False
                    if parsed.get("landmark"):
                        complaint_doc["landmark"] = parsed["landmark"]

                    insert_result = await db[COMPLAINTS_COLLECTION].insert_one(complaint_doc)
                    complaint_id = str(insert_result.inserted_id)

                    cluster_result = await cluster_process_issue(
                        db,
                        category=parsed["category"],
                        location=parsed.get("location") or parsed["ward"],
                        description=complaint_text,
                        complaint_id=complaint_id,
                        source="call",
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
                    complaint_created = True
                    background_tasks.add_task(run_st_dbscan_clustering, db)
                    background_tasks.add_task(update_intensity_scores, db)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process Vapi complaint: {exc}") from exc

    return {
        "status": "success",
        "callId": call_id,
        "eventType": event_type,
        "complaintCreated": complaint_created,
        "complaintId": complaint_id,
    }
