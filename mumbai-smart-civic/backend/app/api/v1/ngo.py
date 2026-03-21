from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import require_ngo
from app.models.complaint_model import COMPLAINTS_COLLECTION, serialize_complaint
from app.models.ngo_request_model import NGO_REQUESTS_COLLECTION
from app.schemas.complaint_schema import ComplaintProgressUpdateItem, ComplaintResponse


router = APIRouter(prefix="/ngo", tags=["NGO Work"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
ALLOWED_PROGRESS_STATUSES = {"In Progress", "Resolved"}


def _resolve_extension(image: UploadFile) -> str:
    suffix = Path((image.filename or "").strip().lower()).suffix
    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return suffix
    if image.content_type == "image/png":
        return ".png"
    if image.content_type == "image/webp":
        return ".webp"
    return ".jpg"


async def _save_progress_image(image: UploadFile) -> str:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Progress image must be an image file")
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Progress image is empty")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Progress image exceeds 8MB")

    ext = _resolve_extension(image)
    file_name = f"{uuid4().hex}{ext}"
    output_path = UPLOAD_DIR / file_name
    output_path.write_bytes(data)
    return f"/static/uploads/{file_name}"


async def _get_assignment_or_403(
    *,
    db: AsyncIOMotorDatabase,
    issue_oid: ObjectId,
    ngo_oid: ObjectId,
) -> tuple[dict, dict]:
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": issue_oid})
    if not complaint:
        raise HTTPException(status_code=404, detail="Issue not found")

    approved_request = await db[NGO_REQUESTS_COLLECTION].find_one(
        {
            "issue_id": {"$in": [issue_oid, str(issue_oid)]},
            "ngo_id": {"$in": [ngo_oid, str(ngo_oid)]},
            "status": "approved",
        }
    )
    if not approved_request:
        raise HTTPException(status_code=403, detail="This issue is not approved for your NGO")

    assigned_ngo_id = complaint.get("assigned_ngo_id")
    if assigned_ngo_id is None:
        # Backfill legacy approved requests that were approved before assignment
        # fields were added to complaints.
        await db[COMPLAINTS_COLLECTION].update_one(
            {"_id": issue_oid},
            {
                "$set": {
                    "assigned_ngo_id": ngo_oid,
                    "assigned_ngo_name": approved_request.get("ngo_name"),
                    "ngo_assisting": True,
                    "assistant_name": approved_request.get("ngo_name"),
                    "progress_status": complaint.get("progress_status") or "Pending",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": issue_oid})
        assigned_ngo_id = complaint.get("assigned_ngo_id") if complaint else None

    if assigned_ngo_id is None or str(assigned_ngo_id) != str(ngo_oid):
        raise HTTPException(status_code=403, detail="This issue is not assigned to your NGO")

    return complaint, approved_request


@router.get("/assigned-issues", response_model=list[ComplaintResponse])
async def list_assigned_issues(
    current_user: dict = Depends(require_ngo()),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ComplaintResponse]:
    ngo_id = current_user.get("id")
    ngo_name = current_user.get("name")
    ngo_oid = ObjectId(ngo_id)
    complaints = await db[COMPLAINTS_COLLECTION].find(
        {
            "assigned_ngo_id": {"$in": [ngo_oid, ngo_id]},
        }
    ).sort("updated_at", -1).to_list(length=500)

    if not complaints:
        approved_requests = await db[NGO_REQUESTS_COLLECTION].find(
            {
                "ngo_id": {"$in": [ngo_oid, ngo_id]},
                "status": "approved",
            },
            {"issue_id": 1},
        ).to_list(length=500)

        issue_ids: list[ObjectId] = []
        for row in approved_requests:
            raw_issue_id = row.get("issue_id")
            if isinstance(raw_issue_id, ObjectId):
                issue_ids.append(raw_issue_id)
                continue
            if isinstance(raw_issue_id, str):
                try:
                    issue_ids.append(ObjectId(raw_issue_id))
                except Exception:
                    continue

        if issue_ids:
            legacy_complaints = await db[COMPLAINTS_COLLECTION].find(
                {"_id": {"$in": issue_ids}}
            ).to_list(length=500)
            for complaint in legacy_complaints:
                if complaint.get("assigned_ngo_id") is None:
                    await db[COMPLAINTS_COLLECTION].update_one(
                        {"_id": complaint["_id"]},
                        {
                            "$set": {
                                "assigned_ngo_id": ngo_oid,
                                "assigned_ngo_name": ngo_name,
                                "ngo_assisting": True,
                                "assistant_name": ngo_name,
                                "progress_status": complaint.get("progress_status") or "Pending",
                                "updated_at": datetime.now(timezone.utc),
                            }
                        },
                    )
            complaints = await db[COMPLAINTS_COLLECTION].find(
                {
                    "assigned_ngo_id": {"$in": [ngo_oid, ngo_id]},
                }
            ).sort("updated_at", -1).to_list(length=500)

    if not complaints:
        return []

    normalized: list[dict] = []
    for complaint in complaints:
        if str(complaint.get("assigned_ngo_id")) == ngo_id:
            normalized.append(complaint)

    return [
        ComplaintResponse.model_validate(serialize_complaint(item))
        for item in normalized
    ]


@router.patch("/issues/{issue_id}/progress", response_model=ComplaintResponse)
async def update_issue_progress(
    issue_id: str,
    status_value: str = Form(..., alias="status"),
    message: str = Form(..., min_length=2, max_length=2000),
    images: list[UploadFile] | None = File(default=None),
    current_user: dict = Depends(require_ngo()),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ComplaintResponse:
    if status_value not in ALLOWED_PROGRESS_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid progress status")

    try:
        issue_oid = ObjectId(issue_id)
        ngo_oid = ObjectId(current_user["id"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid issue id") from exc

    complaint, approved_request = await _get_assignment_or_403(
        db=db,
        issue_oid=issue_oid,
        ngo_oid=ngo_oid,
    )

    image_urls: list[str] = []
    for image in images or []:
        image_urls.append(await _save_progress_image(image))

    now = datetime.now(timezone.utc)
    progress_update = {
        "message": message.strip(),
        "timestamp": now,
        "images": image_urls,
        "status": status_value,
        "ngo_id": str(ngo_oid),
        "ngo_name": current_user.get("name"),
    }

    complaint_update_fields = {
        "progress_status": status_value,
        "status": status_value,
        "updated_at": now,
        "ngo_assisting": True,
        "assistant_name": current_user.get("name"),
        "assigned_ngo_id": ngo_oid,
        "assigned_ngo_name": current_user.get("name"),
    }
    if status_value == "Resolved":
        complaint_update_fields["resolved_at"] = now
        complaint_update_fields["resolved_by"] = {
            "id": current_user.get("id"),
            "name": current_user.get("name"),
            "role": current_user.get("role"),
        }
        if image_urls:
            complaint_update_fields["fixed_image_url"] = image_urls[0]
        if message.strip():
            complaint_update_fields["resolution_note"] = message.strip()
    else:
        complaint_update_fields["resolved_at"] = None
        complaint_update_fields["resolved_by"] = None
        complaint_update_fields["fixed_image_url"] = None

    await db[COMPLAINTS_COLLECTION].update_one(
        {"_id": issue_oid},
        {
            "$set": complaint_update_fields,
            "$push": {"progress_updates": progress_update},
        },
    )

    await db[NGO_REQUESTS_COLLECTION].update_one(
        {"_id": approved_request["_id"]},
        {
            "$set": {
                "updated_at": now,
                "assigned_at": approved_request.get("assigned_at") or now,
            },
        },
    )

    updated = await db[COMPLAINTS_COLLECTION].find_one({"_id": issue_oid})
    if not updated:
        raise HTTPException(status_code=404, detail="Issue not found")

    return ComplaintResponse.model_validate(serialize_complaint(updated))


@router.get("/issues/{issue_id}/updates", response_model=list[ComplaintProgressUpdateItem])
async def get_issue_updates(
    issue_id: str,
    current_user: dict = Depends(require_ngo()),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ComplaintProgressUpdateItem]:
    try:
        issue_oid = ObjectId(issue_id)
        ngo_oid = ObjectId(current_user["id"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid issue id") from exc

    complaint, _ = await _get_assignment_or_403(
        db=db,
        issue_oid=issue_oid,
        ngo_oid=ngo_oid,
    )

    updates = complaint.get("progress_updates") or []
    return [ComplaintProgressUpdateItem.model_validate(item) for item in updates]
