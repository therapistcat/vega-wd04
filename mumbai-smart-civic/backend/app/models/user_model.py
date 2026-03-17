from datetime import datetime, timezone
from typing import Any, Dict


USERS_COLLECTION = "users"


def build_user_document(
    *,
    name: str,
    email: str,
    password_hash: str,
    role: str,
    authority_rank: str | None = None,
    authority_level: int | None = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "email": email.lower(),
        "password_hash": password_hash,
        "role": role,
        "authority_rank": authority_rank,
        "authority_level": authority_level,
        "created_at": now,
        "updated_at": now,
    }


def serialize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "authority_rank": user.get("authority_rank"),
        "authority_level": user.get("authority_level"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "is_blocked": user.get("is_blocked", False),
        "blocked_reason": user.get("blocked_reason"),
        "blocked_at": user.get("blocked_at"),
        "blocked_by": user.get("blocked_by"),
    }
