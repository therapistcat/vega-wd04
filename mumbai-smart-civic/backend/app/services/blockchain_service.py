import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError


LEDGER_COLLECTION = "blockchain_ledger"
GENESIS_SEED = "GENESIS_MUMBAI_CIVIC_CHAIN_2024"
HASH_FIELDS = [
    "id",
    "description",
    "category",
    "status",
    "ward",
    "priority_score",
    "department",
    "user_id",
    "created_at",
]
DEFAULT_DIFFICULTY = 2


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def _normalize_complaint(complaint: dict[str, Any]) -> dict[str, Any]:
    complaint_id = complaint.get("id") or complaint.get("_id")
    if isinstance(complaint_id, ObjectId):
        complaint_id = str(complaint_id)

    department = complaint.get("department") or complaint.get("predicted_department")
    user_id = complaint.get("user_id")
    if isinstance(user_id, ObjectId):
        user_id = str(user_id)

    return {
        "id": complaint_id,
        "description": complaint.get("description"),
        "category": complaint.get("category"),
        "status": complaint.get("status"),
        "ward": complaint.get("ward"),
        "priority_score": complaint.get("priority_score"),
        "department": department,
        "user_id": user_id,
        "created_at": complaint.get("created_at"),
    }


def _compute_data_hash(complaint: dict[str, Any]) -> str:
    normalized = _normalize_complaint(complaint)
    payload = {field: _stringify(normalized.get(field)) for field in HASH_FIELDS}
    return _sha256(json.dumps(payload, sort_keys=True))


def _mine_block(index: int, data_hash: str, prev_hash: str, difficulty: int = DEFAULT_DIFFICULTY) -> tuple[str, int]:
    prefix = "0" * difficulty
    nonce = 0
    while True:
        candidate = _sha256(f"{index}|{data_hash}|{prev_hash}|{nonce}")
        if candidate.startswith(prefix):
            return candidate, nonce
        nonce += 1


def _build_snapshot(complaint: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_complaint(complaint)
    return {
        "complaint_id": _stringify(normalized.get("id")),
        "description": _stringify(normalized.get("description")),
        "status": _stringify(normalized.get("status")),
        "category": _stringify(normalized.get("category")),
        "ward": _stringify(normalized.get("ward")),
        "department": _stringify(normalized.get("department")),
        "priority_score": _stringify(normalized.get("priority_score")),
        "user_id": _stringify(normalized.get("user_id")),
        "created_at": _stringify(normalized.get("created_at")),
    }


def _serialize_block(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(block.get("_id")),
        "index": int(block.get("index", 0)),
        "complaint_id": block.get("complaint_id"),
        "data_hash": block.get("data_hash"),
        "prev_hash": block.get("prev_hash"),
        "block_hash": block.get("block_hash"),
        "nonce": int(block.get("nonce", 0)),
        "difficulty": int(block.get("difficulty", DEFAULT_DIFFICULTY)),
        "algorithm": block.get("algorithm", "sha256"),
        "is_genesis": bool(block.get("is_genesis", False)),
        "mined_at": block.get("mined_at"),
        "complaint_snapshot": block.get("complaint_snapshot"),
    }


async def ensure_genesis(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    existing = await db[LEDGER_COLLECTION].find_one({"is_genesis": True})
    if existing:
        return existing

    data_hash = _sha256(GENESIS_SEED)
    prev_hash = "0" * 64
    block_hash, nonce = _mine_block(index=0, data_hash=data_hash, prev_hash=prev_hash, difficulty=DEFAULT_DIFFICULTY)
    now = datetime.now(timezone.utc)
    genesis = {
        "index": 0,
        "complaint_id": None,
        "data_hash": data_hash,
        "prev_hash": prev_hash,
        "block_hash": block_hash,
        "nonce": nonce,
        "difficulty": DEFAULT_DIFFICULTY,
        "algorithm": "sha256",
        "is_genesis": True,
        "mined_at": now,
        "complaint_snapshot": {
            "description": "Genesis block for Mumbai Smart Civic complaint ledger",
        },
    }
    await db[LEDGER_COLLECTION].update_one(
        {"is_genesis": True},
        {"$setOnInsert": genesis},
        upsert=True,
    )
    stored = await db[LEDGER_COLLECTION].find_one({"is_genesis": True})
    if not stored:
        raise RuntimeError("Failed to initialize blockchain genesis block")
    return stored


async def get_chain_tip(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    await ensure_genesis(db)
    rows = await db[LEDGER_COLLECTION].find({}).sort("index", -1).to_list(length=1)
    return rows[0]


async def get_block_by_complaint_id(db: AsyncIOMotorDatabase, complaint_id: str) -> dict[str, Any] | None:
    await ensure_genesis(db)
    return await db[LEDGER_COLLECTION].find_one({"complaint_id": complaint_id})


async def anchor_complaint(db: AsyncIOMotorDatabase, complaint: dict[str, Any]) -> dict[str, Any]:
    await ensure_genesis(db)
    normalized = _normalize_complaint(complaint)
    complaint_id = _stringify(normalized.get("id"))
    if not complaint_id:
        raise ValueError("Complaint id is required for blockchain anchoring")

    existing = await get_block_by_complaint_id(db, complaint_id)
    if existing:
        return {"created": False, "block": _serialize_block(existing)}

    tip = await get_chain_tip(db)
    index = int(tip.get("index", 0)) + 1
    prev_hash = str(tip.get("block_hash", "0" * 64))
    data_hash = _compute_data_hash(normalized)
    block_hash, nonce = _mine_block(index=index, data_hash=data_hash, prev_hash=prev_hash, difficulty=DEFAULT_DIFFICULTY)
    now = datetime.now(timezone.utc)
    block_doc = {
        "index": index,
        "complaint_id": complaint_id,
        "data_hash": data_hash,
        "prev_hash": prev_hash,
        "block_hash": block_hash,
        "nonce": nonce,
        "difficulty": DEFAULT_DIFFICULTY,
        "algorithm": "sha256",
        "is_genesis": False,
        "mined_at": now,
        "complaint_snapshot": _build_snapshot(normalized),
    }

    try:
        insert_result = await db[LEDGER_COLLECTION].insert_one(block_doc)
        block_doc["_id"] = insert_result.inserted_id
        return {"created": True, "block": _serialize_block(block_doc)}
    except DuplicateKeyError:
        # Safe idempotency for concurrent anchor calls on same complaint.
        existing_after_race = await get_block_by_complaint_id(db, complaint_id)
        if existing_after_race:
            return {"created": False, "block": _serialize_block(existing_after_race)}
        raise


async def verify_complaint(db: AsyncIOMotorDatabase, complaint: dict[str, Any]) -> dict[str, Any]:
    await ensure_genesis(db)
    normalized = _normalize_complaint(complaint)
    complaint_id = _stringify(normalized.get("id"))
    if not complaint_id:
        raise ValueError("Complaint id is required for blockchain verification")

    block = await get_block_by_complaint_id(db, complaint_id)
    if not block:
        return {
            "complaint_id": complaint_id,
            "anchored": False,
            "valid": False,
            "reason": "No blockchain block found for complaint",
        }

    on_chain_data_hash = _stringify(block.get("data_hash"))
    expected_data_hash = _compute_data_hash(normalized)
    index = int(block.get("index", 0))
    prev_hash = _stringify(block.get("prev_hash"))
    nonce = int(block.get("nonce", 0))
    difficulty = int(block.get("difficulty", DEFAULT_DIFFICULTY))
    block_hash = _stringify(block.get("block_hash"))

    recomputed_block_hash = _sha256(f"{index}|{on_chain_data_hash}|{prev_hash}|{nonce}")
    pow_valid = recomputed_block_hash.startswith("0" * difficulty) and recomputed_block_hash == block_hash

    prev_link_valid = True
    if index > 0:
        prev_block = await db[LEDGER_COLLECTION].find_one({"index": index - 1})
        prev_link_valid = bool(prev_block) and _stringify(prev_block.get("block_hash")) == prev_hash

    data_hash_match = expected_data_hash == on_chain_data_hash
    valid = data_hash_match and pow_valid and prev_link_valid

    return {
        "complaint_id": complaint_id,
        "anchored": True,
        "valid": valid,
        "data_hash_match": data_hash_match,
        "pow_valid": pow_valid,
        "prev_link_valid": prev_link_valid,
        "expected_data_hash": expected_data_hash,
        "on_chain_data_hash": on_chain_data_hash,
        "block_index": index,
        "block_hash": block_hash,
    }


async def get_full_chain(db: AsyncIOMotorDatabase, limit: int = 200) -> list[dict[str, Any]]:
    await ensure_genesis(db)
    safe_limit = max(1, min(limit, 2000))
    docs = await db[LEDGER_COLLECTION].find({}).sort("index", -1).to_list(length=safe_limit)
    return [_serialize_block(doc) for doc in docs]
