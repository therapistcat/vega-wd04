from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.database import get_database
from app.core.security import require_authority, require_ngo
from app.blockchain.ledger_service import log_ngo_assigned
from app.models.ngo_request_model import (
    NGO_REQUESTS_COLLECTION,
    build_ngo_request_document,
    serialize_ngo_request,
)
from app.schemas.ngo_request_schema import (
    NGORequestCreate,
    NGORequestUpdate,
    NGORequestResponse,
)
from app.models.complaint_model import COMPLAINTS_COLLECTION, serialize_complaint
from app.schemas.complaint_schema import ComplaintResponse

router = APIRouter(prefix="/ngo-requests", tags=["NGO Requests"])

@router.post("", response_model=NGORequestResponse, status_code=status.HTTP_201_CREATED)
async def create_ngo_request(
    payload: NGORequestCreate,
    current_user: dict = Depends(require_ngo()),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> NGORequestResponse:
    print("NGO request payload:", payload.model_dump())
    print("User:", current_user)

    try:
        issue_oid = ObjectId(payload.issue_id)
        ngo_oid = ObjectId(current_user["id"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid issue id") from exc

    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": issue_oid})
    if not complaint:
        raise HTTPException(status_code=404, detail="Issue not found")

    existing = await db[NGO_REQUESTS_COLLECTION].find_one({
        "issue_id": issue_oid,
        "ngo_id": ngo_oid,
    })
    if existing:
        raise HTTPException(status_code=400, detail="Request already sent")

    document = build_ngo_request_document(
        issue_id=payload.issue_id,
        issue_title=payload.issue_title or complaint.get("description") or "",
        ngo_id=current_user["id"],
        ngo_name=current_user["name"],
    )
    result = await db[NGO_REQUESTS_COLLECTION].insert_one(document)
    created = await db[NGO_REQUESTS_COLLECTION].find_one({"_id": result.inserted_id})
    return NGORequestResponse.model_validate(serialize_ngo_request(created))

@router.get("", response_model=list[NGORequestResponse])
async def list_all_ngo_requests(
    current_user: dict = Depends(require_authority(1)),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[NGORequestResponse]:
    _ = current_user
    cursor = db[NGO_REQUESTS_COLLECTION].find({}).sort("created_at", -1)
    requests = await cursor.to_list(length=500)
    return [NGORequestResponse.model_validate(serialize_ngo_request(r)) for r in requests]

@router.get("/me", response_model=list[NGORequestResponse])
async def list_my_requests(
    current_user: dict = Depends(require_ngo()),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[NGORequestResponse]:
    ngo_oid = ObjectId(current_user["id"])
    cursor = db[NGO_REQUESTS_COLLECTION].find(
        {"ngo_id": {"$in": [ngo_oid, current_user["id"]]}}
    ).sort("created_at", -1)
    requests = await cursor.to_list(length=100)
    return [NGORequestResponse.model_validate(serialize_ngo_request(r)) for r in requests]

@router.get("/available-issues", response_model=list[ComplaintResponse])
async def list_available_issues(
    current_user: dict = Depends(require_ngo()),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ComplaintResponse]:
    _ = current_user
    # NGOs should only see open complaints that are not already assigned.
    cursor = db[COMPLAINTS_COLLECTION].find({"status": "Open", "assigned_ngo_id": None})
    complaints = await cursor.to_list(length=500)
    
    # Enrichment logic for NGOs
    complaint_ids = [c["_id"] for c in complaints]
    ngo_requests = await db[NGO_REQUESTS_COLLECTION].find({
        "issue_id": {"$in": complaint_ids}
    }).to_list(length=1000)

    ngo_map = {}
    for req in ngo_requests:
        issue_id = str(req["issue_id"])
        if issue_id not in ngo_map:
            ngo_map[issue_id] = {"count": 0, "assisting": False}
        ngo_map[issue_id]["count"] += 1
        if req["status"] == "approved":
            ngo_map[issue_id]["assisting"] = True

    response_list = []
    for item in complaints:
        serialized = serialize_complaint(item)
        metadata = ngo_map.get(serialized["id"], {"count": 0, "assisting": False})
        serialized["ngo_request_count"] = metadata["count"]
        serialized["ngo_assisting"] = metadata["assisting"]
        response_list.append(ComplaintResponse.model_validate(serialized))

    return response_list

@router.patch("/{request_id}", response_model=NGORequestResponse)
async def update_request_status(
    request_id: str,
    payload: NGORequestUpdate,
    current_user: dict = Depends(require_authority(1)),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> NGORequestResponse:
    _ = current_user
    try:
        oid = ObjectId(request_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid request id") from exc

    existing_request = await db[NGO_REQUESTS_COLLECTION].find_one({"_id": oid})
    if not existing_request:
        raise HTTPException(status_code=404, detail="Request not found")

    now = datetime.now(timezone.utc)
    request_update_fields = {
        "status": payload.status,
        "updated_at": now,
    }

    if payload.status == "approved":
        complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": existing_request["issue_id"]})
        if not complaint:
            raise HTTPException(status_code=404, detail="Issue not found")

        assigned_ngo_id = complaint.get("assigned_ngo_id")
        if assigned_ngo_id is not None and str(assigned_ngo_id) != str(existing_request["ngo_id"]):
            raise HTTPException(status_code=400, detail="Issue already assigned to another NGO")

        request_update_fields["assigned_at"] = now

        await db[COMPLAINTS_COLLECTION].update_one(
            {"_id": existing_request["issue_id"]},
            {
                "$set": {
                    "assigned_ngo_id": existing_request["ngo_id"],
                    "assigned_ngo_name": existing_request.get("ngo_name"),
                    "ngo_assisting": True,
                    "assistant_name": existing_request.get("ngo_name"),
                    "progress_status": complaint.get("progress_status") or "Pending",
                    "updated_at": now,
                }
            },
        )
    elif payload.status == "rejected":
        request_update_fields["assigned_at"] = None
        await db[COMPLAINTS_COLLECTION].update_one(
            {
                "_id": existing_request["issue_id"],
                "assigned_ngo_id": existing_request["ngo_id"],
            },
            {
                "$set": {
                    "assigned_ngo_id": None,
                    "assigned_ngo_name": None,
                    "ngo_assisting": False,
                    "assistant_name": None,
                    "updated_at": now,
                }
            },
        )

    result = await db[NGO_REQUESTS_COLLECTION].find_one_and_update(
        {"_id": oid},
        {"$set": request_update_fields},
        return_document=ReturnDocument.AFTER,
    )

    if payload.status == "approved":
        updated_issue = await db[COMPLAINTS_COLLECTION].find_one({"_id": existing_request["issue_id"]})
        if updated_issue:
            await log_ngo_assigned(
                db,
                issue=updated_issue,
                actor=current_user,
                ngo_name=existing_request.get("ngo_name"),
            )

    return NGORequestResponse.model_validate(serialize_ngo_request(result))
