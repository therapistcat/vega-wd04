import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


def stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=stringify_value)
    return str(value)


def sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_json_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=stringify_value)
    return sha256_hex(normalized)
