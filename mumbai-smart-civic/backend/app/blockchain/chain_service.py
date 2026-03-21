from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.blockchain.block import AuditBlock


LEDGER_COLLECTION = "blockchain_ledger"
CHAIN_TYPE = "audit"
COUNTERS_COLLECTION = "blockchain_counters"


def _serialize_block(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document.get("_id")),
        "index": int(document.get("index", 0)),
        "timestamp": document.get("timestamp"),
        "data": document.get("data") or {},
        "previous_hash": str(document.get("previous_hash") or document.get("prev_hash") or ""),
        "hash": str(document.get("hash") or document.get("block_hash") or ""),
        "algorithm": document.get("algorithm", "sha256"),
        "is_genesis": bool(document.get("is_genesis", False)),
    }


async def ensure_genesis_block(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    existing = await db[LEDGER_COLLECTION].find_one({"chain_type": CHAIN_TYPE, "is_genesis": True})
    if existing:
        return existing

    genesis = AuditBlock.genesis().to_document()
    await db[LEDGER_COLLECTION].update_one(
        {"chain_type": CHAIN_TYPE, "is_genesis": True},
        {"$setOnInsert": genesis},
        upsert=True,
    )
    stored = await db[LEDGER_COLLECTION].find_one({"chain_type": CHAIN_TYPE, "is_genesis": True})
    if not stored:
        raise RuntimeError("Failed to initialize audit genesis block")
    return stored


async def _next_index(db: AsyncIOMotorDatabase) -> int:
    counter = await db[COUNTERS_COLLECTION].find_one_and_update(
        {"_id": f"{CHAIN_TYPE}_index"},
        {"$inc": {"value": 1}, "$setOnInsert": {"value": 0}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(counter.get("value", 0))


async def get_chain_tip(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    await ensure_genesis_block(db)
    tip = await db[LEDGER_COLLECTION].find_one({"chain_type": CHAIN_TYPE}, sort=[("index", -1)])
    if not tip:
        raise RuntimeError("Audit chain tip is unavailable")
    return tip


async def add_block(db: AsyncIOMotorDatabase, data: dict[str, Any]) -> dict[str, Any]:
    await ensure_genesis_block(db)
    tip = await get_chain_tip(db)
    next_index = await _next_index(db)

    if next_index == 0:
        next_index = 1
    if int(tip.get("index", 0)) >= next_index:
        next_index = int(tip.get("index", 0)) + 1

    block = AuditBlock(
        index=next_index,
        timestamp=datetime.now(timezone.utc),
        data=data,
        previous_hash=str(tip.get("hash") or tip.get("block_hash") or "0" * 64),
    )
    document = block.to_document()
    result = await db[LEDGER_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return _serialize_block(document)


async def get_chain(db: AsyncIOMotorDatabase, *, limit: int = 500) -> list[dict[str, Any]]:
    await ensure_genesis_block(db)
    safe_limit = max(1, min(limit, 5000))
    docs = await db[LEDGER_COLLECTION].find({"chain_type": CHAIN_TYPE}).sort("index", -1).to_list(length=safe_limit)
    return [_serialize_block(item) for item in docs]


async def get_blocks_for_issue(db: AsyncIOMotorDatabase, issue_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    await ensure_genesis_block(db)
    safe_limit = max(1, min(limit, 1000))
    docs = await db[LEDGER_COLLECTION].find(
        {"chain_type": CHAIN_TYPE, "data.issue_id": issue_id}
    ).sort("index", -1).to_list(length=safe_limit)
    return [_serialize_block(item) for item in docs]
