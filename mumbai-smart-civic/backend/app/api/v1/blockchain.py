from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import require_roles
from app.blockchain.chain_service import get_blocks_for_issue, get_chain
from app.blockchain.verifier import verify_chain_integrity
from app.models.complaint_model import COMPLAINTS_COLLECTION, serialize_complaint
from app.services.blockchain_service import (
    LEDGER_COLLECTION,
    anchor_complaint,
    get_full_chain,
    get_chain_tip,
    verify_complaint,
)


router = APIRouter(prefix="/blockchain", tags=["blockchain"])


def _to_object_id(raw: str) -> ObjectId:
    try:
        return ObjectId(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid complaint id") from exc


def _assert_complaint_access(current_user: dict, complaint: dict) -> None:
    if current_user.get("role") != "citizen":
        return
    if str(complaint.get("user_id")) != current_user.get("id"):
        raise HTTPException(status_code=403, detail="You are not authorized to access this complaint")


async def _get_complaint_doc_or_404(db: AsyncIOMotorDatabase, complaint_id: str) -> dict:
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": _to_object_id(complaint_id)})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.get("/chain")
async def read_chain(
    limit: int = Query(default=200, ge=1, le=2000),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    blocks = await get_full_chain(db, limit=limit)
    if current_user.get("role") == "citizen":
        own_ids_raw = await db[COMPLAINTS_COLLECTION].find(
            {"user_id": ObjectId(current_user["id"])},
            {"_id": 1},
        ).to_list(length=5000)
        own_ids = {str(row["_id"]) for row in own_ids_raw}
        blocks = [
            block
            for block in blocks
            if block.get("is_genesis") or (block.get("complaint_id") in own_ids)
        ][:limit]

    total_blocks = await db[LEDGER_COLLECTION].count_documents({})
    tip = await get_chain_tip(db)

    return {
        "items": blocks,
        "stats": {
            "total_blocks": int(total_blocks),
            "chain_length": int(total_blocks),
            "last_block_hash": str(tip.get("block_hash", "")),
            "difficulty": int(tip.get("difficulty", 2)),
        },
    }


@router.get("/ledger")
async def read_audit_ledger(
    limit: int = Query(default=300, ge=1, le=2000),
    current_user: dict = Depends(require_roles(["authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    _ = current_user
    items = await get_chain(db, limit=limit)
    verification = await verify_chain_integrity(db)
    return {
        "items": items,
        "verification": verification,
        "stats": {
            "total_blocks": len(items),
        },
    }


@router.get("/issue/{issue_id}")
async def read_issue_audit_trail(
    issue_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin", "ngo"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    complaint = await _get_complaint_doc_or_404(db, issue_id)
    _assert_complaint_access(current_user, complaint)
    items = await get_blocks_for_issue(db, issue_id, limit=limit)
    return {
        "issue_id": issue_id,
        "items": items,
    }


@router.get("/verify")
async def verify_audit_ledger(
    current_user: dict = Depends(require_roles(["authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    _ = current_user
    return await verify_chain_integrity(db)


@router.post("/anchor/{complaint_id}")
async def anchor_single_complaint(
    complaint_id: str,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    complaint_doc = await _get_complaint_doc_or_404(db, complaint_id)
    _assert_complaint_access(current_user, complaint_doc)

    complaint_payload = serialize_complaint(
        complaint_doc,
        viewer_user_id=current_user.get("id"),
    )
    result = await anchor_complaint(db, complaint_payload)
    return result


@router.get("/verify/{complaint_id}")
async def verify_single_complaint(
    complaint_id: str,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    complaint_doc = await _get_complaint_doc_or_404(db, complaint_id)
    _assert_complaint_access(current_user, complaint_doc)

    complaint_payload = serialize_complaint(
        complaint_doc,
        viewer_user_id=current_user.get("id"),
    )
    return await verify_complaint(db, complaint_payload)


@router.post("/anchor-all")
async def anchor_all_for_current_user(
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    user_id = _to_object_id(current_user["id"])
    complaints = await db[COMPLAINTS_COLLECTION].find({"user_id": user_id}).sort("created_at", 1).to_list(length=5000)

    anchored_new = 0
    already_anchored = 0
    blocks = []
    for complaint_doc in complaints:
        payload = serialize_complaint(complaint_doc, viewer_user_id=current_user.get("id"))
        result = await anchor_complaint(db, payload)
        if result.get("created"):
            anchored_new += 1
        else:
            already_anchored += 1
        block = result.get("block")
        if block:
            blocks.append(block)

    return {
        "total_considered": len(complaints),
        "anchored_new": anchored_new,
        "already_anchored": already_anchored,
        "blocks": blocks[:200],
    }
