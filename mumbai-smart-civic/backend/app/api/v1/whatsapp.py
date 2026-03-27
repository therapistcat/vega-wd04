from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.services.whatsapp_service import handle_incoming_message


router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _decode_media_field(payload: dict[str, Any], media_key: str) -> dict[str, Any]:
    media = payload.get(media_key) or {}
    base64_data = str(media.get("base64") or media.get("data") or "").strip()
    if not base64_data:
        raise ValueError(f"Missing base64 media data for {media_key}")
    return {
        "type": media_key,
        media_key: {
            "bytes": base64.b64decode(base64_data),
            "mime_type": media.get("mime_type") or media.get("mimetype") or "application/octet-stream",
        },
    }


def _normalize_bridge_payload(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    phone = str(payload.get("phone") or payload.get("phone_number") or payload.get("from") or "").strip()
    if not phone:
        raise ValueError("Missing phone number")

    message_type = str(payload.get("type") or "").strip().lower()
    if message_type == "text":
        return phone, {
            "type": "text",
            "text": {"body": str(payload.get("text") or payload.get("body") or "").strip()},
        }
    if message_type == "audio":
        return phone, _decode_media_field(payload, "audio")
    if message_type == "image":
        return phone, _decode_media_field(payload, "image")
    if message_type == "video":
        return phone, _decode_media_field(payload, "video")
    if message_type == "location":
        location = payload.get("location") or {}
        return phone, {
            "type": "location",
            "location": {
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            },
        }
    raise ValueError(f"Unsupported message type: {message_type or 'unknown'}")


@router.post("/message")
async def whatsapp_message(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _ = authorization
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        phone, normalized_message = _normalize_bridge_payload(body)
        result = await handle_incoming_message(
            db,
            background_tasks,
            phone=phone,
            message=normalized_message,
            raw_payload=body,
        )
        return {"status": "ok", "result": result}
    except Exception as exc:
        print(f"[whatsapp-bridge] message failure: {exc}")
        try:
            await db["vapi_events"].insert_one(
                {
                    "receivedAt": datetime.now(timezone.utc),
                    "type": "whatsapp_bridge_failure",
                    "phone": body.get("phone") or body.get("phone_number"),
                    "phone_number": body.get("phone") or body.get("phone_number"),
                    "via": "whatsapp",
                    "payload": body,
                    "error": str(exc),
                }
            )
        except Exception:
            pass
        return {"status": "ok", "error": str(exc)}
