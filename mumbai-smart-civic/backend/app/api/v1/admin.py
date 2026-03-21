from datetime import datetime, timezone
import math
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.database import get_database
from app.core.security import require_authority
from app.models.complaint_model import COMPLAINTS_COLLECTION, serialize_complaint
from app.schemas.complaint_schema import (
    ComplaintResponse,
    ComplaintStatusUpdateRequest,
    SpatialAnalyticsPoint,
)
from app.models.ngo_request_model import NGO_REQUESTS_COLLECTION
from app.services.spatial_service import compute_spatial_analytics


router = APIRouter(prefix="/a", tags=["authority"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def _as_utc_datetime(value: datetime | None) -> datetime:
    if not isinstance(value, datetime):
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _authority_rank_score(complaint: dict, now: datetime) -> float:
    created_at = _as_utc_datetime(complaint.get("created_at"))
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    upvotes = float(complaint.get("upvotes_count") or 0.0)
    priority = float(complaint.get("priority_score") or 0.0)

    vote_decay = math.pow(0.5, age_hours / 24.0)
    fresh_bonus = max(0.0, 2.0 - (age_hours / 12.0))
    status = str(complaint.get("status") or "").strip().lower()
    status_bonus = 0.8 if status == "open" else (0.4 if status == "in progress" else -0.5)

    return (upvotes * vote_decay * 2.5) + (priority * 2.0) + fresh_bonus + status_bonus


def _resolve_extension(image: UploadFile) -> str:
    suffix = Path((image.filename or "").strip().lower()).suffix
    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return suffix
    if image.content_type == "image/png":
        return ".png"
    if image.content_type == "image/webp":
        return ".webp"
    return ".jpg"


async def _save_resolution_image(image: UploadFile) -> str:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Fixed-work image must be an image file")
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Fixed-work image is empty")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fixed-work image exceeds 8MB")

    ext = _resolve_extension(image)
    file_name = f"{uuid4().hex}{ext}"
    output_path = UPLOAD_DIR / file_name
    output_path.write_bytes(data)
    return f"/static/uploads/{file_name}"


@router.get("/complaints", response_model=list[ComplaintResponse])
async def list_all_complaints(
    current_user: dict = Depends(require_authority(settings.authority_min_level_list)),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ComplaintResponse]:
    cursor = db[COMPLAINTS_COLLECTION].find({})
    complaints = await cursor.to_list(length=500)
    now = datetime.now(timezone.utc)
    
    # Sort complaints as before
    complaints.sort(
        key=lambda row: (
            _authority_rank_score(row, now),
            _as_utc_datetime(row.get("updated_at") or row.get("created_at")),
        ),
        reverse=True,
    )

    # Fetch NGO requests for these complaints to add metadata
    complaint_ids = [c["_id"] for c in complaints]
    ngo_requests = await db[NGO_REQUESTS_COLLECTION].find({
        "issue_id": {"$in": complaint_ids}
    }).to_list(length=1000)

    # Build lookup map
    ngo_map = {}
    for req in ngo_requests:
        issue_id = str(req["issue_id"])
        if issue_id not in ngo_map:
            ngo_map[issue_id] = {"count": 0, "assisting": False, "assistant": None}
        ngo_map[issue_id]["count"] += 1
        if req["status"] == "approved":
            ngo_map[issue_id]["assisting"] = True
            ngo_map[issue_id]["assistant"] = req["ngo_name"]

    response_list = []
    for item in complaints:
        serialized = serialize_complaint(item)
        metadata = ngo_map.get(serialized["id"], {"count": 0, "assisting": False, "assistant": None})
        serialized["ngo_request_count"] = metadata["count"]
        serialized["ngo_assisting"] = metadata["assisting"]
        serialized["assistant_name"] = metadata["assistant"]
        response_list.append(ComplaintResponse.model_validate(serialized))

    return response_list


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    complaint_id: str,
    payload: ComplaintStatusUpdateRequest,
    current_user: dict = Depends(
        require_authority(settings.authority_min_level_status_update)
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ComplaintResponse:
    try:
        oid = ObjectId(complaint_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid complaint id") from exc

    progress_status = "Pending" if payload.status == "Open" else payload.status
    update_fields = {
        "status": payload.status,
        "progress_status": progress_status,
        "updated_at": datetime.now(timezone.utc),
    }
    unset_fields = {}
    if payload.status != "Resolved":
        unset_fields = {
            "resolved_at": "",
            "resolved_by": "",
            "fixed_image_url": "",
        }

    await db[COMPLAINTS_COLLECTION].update_one(
        {"_id": oid},
        {
            "$set": update_fields,
            **({"$unset": unset_fields} if unset_fields else {}),
        },
    )

    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": oid})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    return ComplaintResponse.model_validate(serialize_complaint(complaint))


@router.post("/complaints/{complaint_id}/status-with-proof", response_model=ComplaintResponse)
async def update_complaint_status_with_proof(
    complaint_id: str,
    status_value: str = Form(..., alias="status"),
    resolution_note: str | None = Form(default=None, max_length=2000),
    fixed_image: UploadFile | None = File(default=None),
    current_user: dict = Depends(
        require_authority(settings.authority_min_level_status_update)
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ComplaintResponse:
    valid_statuses = {"Open", "In Progress", "Resolved"}
    if status_value not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    try:
        oid = ObjectId(complaint_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid complaint id") from exc

    if status_value == "Resolved" and fixed_image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolved complaints must include fixed-work image proof",
        )

    fixed_image_url = None
    if fixed_image is not None:
        fixed_image_url = await _save_resolution_image(fixed_image)

    update_fields = {
        "status": status_value,
        "progress_status": "Pending" if status_value == "Open" else status_value,
        "resolution_note": resolution_note,
        "updated_at": datetime.now(timezone.utc),
    }
    if fixed_image_url is not None:
        update_fields["fixed_image_url"] = fixed_image_url
    if status_value == "Resolved":
        update_fields["resolved_by"] = {
            "id": current_user.get("id"),
            "name": current_user.get("name"),
            "role": current_user.get("role"),
            "authority_rank": current_user.get("authority_rank"),
        }
        update_fields["resolved_at"] = datetime.now(timezone.utc)
        await db[COMPLAINTS_COLLECTION].update_one({"_id": oid}, {"$set": update_fields})
    else:
        await db[COMPLAINTS_COLLECTION].update_one(
            {"_id": oid},
            {
                "$set": update_fields,
                "$unset": {
                    "resolved_at": "",
                    "resolved_by": "",
                    "fixed_image_url": "",
                },
            },
        )
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": oid})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    return ComplaintResponse.model_validate(serialize_complaint(complaint))


@router.get("/spatial-analytics", response_model=list[SpatialAnalyticsPoint])
async def spatial_analytics(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=3000, ge=100, le=50000),
    window_hours: int = Query(default=720, ge=1, le=7000),
    current_user: dict = Depends(
        require_authority(settings.authority_min_level_spatial_analytics)
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[SpatialAnalyticsPoint]:
    points = await compute_spatial_analytics(
        db, 
        lat=lat, 
        lng=lng, 
        radius_m=radius_m, 
        window_hours=window_hours
    )
    return [SpatialAnalyticsPoint.model_validate(point) for point in points]
