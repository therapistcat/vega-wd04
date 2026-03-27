from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


WHATSAPP_SESSIONS_COLLECTION = "whatsapp_sessions"
SESSION_TTL_MINUTES = 30

STATE_IDLE = "IDLE"
STATE_AWAITING_COMPLAINT = "AWAITING_COMPLAINT"
STATE_AWAITING_IMAGE = "AWAITING_IMAGE"
STATE_AWAITING_LOCATION = "AWAITING_LOCATION"
STATE_PROCESSING = "PROCESSING"
STATE_DONE = "DONE"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expiry() -> datetime:
    return _now() + timedelta(minutes=SESSION_TTL_MINUTES)


def _session_base(phone_number: str) -> dict[str, Any]:
    now = _now()
    expires_at = _expiry()
    return {
        "phone": phone_number,
        "phone_number": phone_number,
        "state": STATE_AWAITING_COMPLAINT,
        "current_step": STATE_AWAITING_COMPLAINT,
        "complaint_text": "",
        "complaint_text_original": "",
        "image_path": "",
        "detected_category": "",
        "location": None,
        "temp_data": {
            "complaint_text": "",
            "complaint_text_original": "",
            "image_path": "",
            "detected_category": "",
            "location": None,
        },
        "created_at": now,
        "updated_at": now,
        "expires_at": expires_at,
    }


async def get_session(db: AsyncIOMotorDatabase, phone_number: str) -> dict[str, Any] | None:
    return await db[WHATSAPP_SESSIONS_COLLECTION].find_one({"phone_number": phone_number})


async def start_session(db: AsyncIOMotorDatabase, phone_number: str) -> dict[str, Any]:
    session = _session_base(phone_number)
    await db[WHATSAPP_SESSIONS_COLLECTION].update_one(
        {"phone_number": phone_number},
        {"$set": session},
        upsert=True,
    )
    stored = await get_session(db, phone_number)
    return stored or session


async def refresh_session(db: AsyncIOMotorDatabase, phone_number: str) -> dict[str, Any]:
    await db[WHATSAPP_SESSIONS_COLLECTION].update_one(
        {"phone_number": phone_number},
        {
            "$set": {
                "updated_at": _now(),
                "expires_at": _expiry(),
            }
        },
    )
    stored = await get_session(db, phone_number)
    if stored is None:
        return await start_session(db, phone_number)
    return stored


async def update_session(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    *,
    state: str | None = None,
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    update_fields = {
        "updated_at": _now(),
        "expires_at": _expiry(),
    }
    if state is not None:
        update_fields["state"] = state
        update_fields["current_step"] = state
    if fields:
        update_fields.update(fields)
        temp_data = {}
        for key in ("complaint_text", "complaint_text_original", "image_path", "detected_category", "location"):
            if key in fields:
                temp_data[key] = fields[key]
        if temp_data:
            update_fields["temp_data"] = temp_data
    await db[WHATSAPP_SESSIONS_COLLECTION].update_one(
        {"phone_number": phone_number},
        {"$set": update_fields},
        upsert=True,
    )
    stored = await get_session(db, phone_number)
    return stored or {**_session_base(phone_number), **update_fields}


async def complete_session(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    *,
    complaint_id: str | None = None,
) -> None:
    await db[WHATSAPP_SESSIONS_COLLECTION].update_one(
        {"phone_number": phone_number},
        {
            "$set": {
                "state": STATE_IDLE,
                "current_step": STATE_IDLE,
                "complaint_id": complaint_id,
                "updated_at": _now(),
                "expires_at": _expiry(),
            }
        },
    )


async def reset_session(db: AsyncIOMotorDatabase, phone_number: str) -> None:
    await db[WHATSAPP_SESSIONS_COLLECTION].delete_one({"phone_number": phone_number})
