from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.blockchain.hash_utils import stable_json_hash, stringify_value
from app.blockchain.chain_service import CHAIN_TYPE, LEDGER_COLLECTION, ensure_genesis_block


def _expected_hash(block: dict[str, Any]) -> str:
    return stable_json_hash(
        {
            "index": int(block.get("index", 0)),
            "timestamp": stringify_value(block.get("timestamp")),
            "data": block.get("data") or {},
            "previous_hash": str(block.get("previous_hash") or ""),
        }
    )


async def verify_chain_integrity(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    await ensure_genesis_block(db)
    blocks = await db[LEDGER_COLLECTION].find({"chain_type": CHAIN_TYPE}).sort("index", 1).to_list(length=10000)
    if not blocks:
        return {"valid": True, "checked_blocks": 0, "failure_index": None}

    previous_hash = None
    for block in blocks:
        current_hash = str(block.get("hash") or "")
        expected_hash = _expected_hash(block)
        if current_hash != expected_hash:
            return {
                "valid": False,
                "checked_blocks": len(blocks),
                "failure_index": int(block.get("index", 0)),
                "reason": "Hash mismatch detected",
            }

        if previous_hash is None:
            if str(block.get("previous_hash") or "") != "0" * 64:
                return {
                    "valid": False,
                    "checked_blocks": len(blocks),
                    "failure_index": int(block.get("index", 0)),
                    "reason": "Genesis previous hash is invalid",
                }
        elif str(block.get("previous_hash") or "") != previous_hash:
            return {
                "valid": False,
                "checked_blocks": len(blocks),
                "failure_index": int(block.get("index", 0)),
                "reason": "Previous hash link is broken",
            }

        previous_hash = current_hash

    return {
        "valid": True,
        "checked_blocks": len(blocks),
        "failure_index": None,
        "last_hash": previous_hash,
    }
