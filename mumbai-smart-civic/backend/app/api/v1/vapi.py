from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import verify_vapi_token


router = APIRouter(prefix="/vapi", tags=["vapi"])


@router.get("/ping")
async def vapi_ping(_: bool = Depends(verify_vapi_token)) -> dict[str, Any]:
    return {"ok": True, "service": "vapi", "authenticated": True}


@router.post("/webhook")
async def vapi_webhook(
    payload: dict[str, Any],
    _: bool = Depends(verify_vapi_token),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    call_id = (
        str(payload.get("call", {}).get("id") or "")
        or str(payload.get("message", {}).get("call", {}).get("id") or "")
    )
    event_type = str(payload.get("type") or payload.get("event") or payload.get("message", {}).get("type") or "unknown")

    await db["vapi_events"].insert_one(
        {
            "call_id": call_id or None,
            "event_type": event_type,
            "payload": payload,
            "created_at": now,
        }
    )

    return {
        "ok": True,
        "received": True,
        "event_type": event_type,
        "call_id": call_id or None,
        "timestamp": now.isoformat(),
    }
