from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.config import settings
from app.services.whatsapp_service import extract_messages, process_whatsapp_message


router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def whatsapp_verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Any:
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else (hub_challenge or "")
    return {"status": "verification_failed"}


@router.post("/webhook")
async def whatsapp_webhook(
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

    results: list[dict[str, Any]] = []
    try:
        messages = extract_messages(body)
        if not messages:
            await db["vapi_events"].insert_one(
                {
                    "receivedAt": datetime.now(timezone.utc),
                    "type": "whatsapp_raw",
                    "phone": None,
                    "via": "whatsapp",
                    "payload": body,
                }
            )
        for wrapped in messages:
            result = await process_whatsapp_message(
                db,
                background_tasks,
                wrapped_message=wrapped,
            )
            results.append(result)
    except Exception as exc:
        print(f"[whatsapp] webhook failure: {exc}")
        try:
            await db["vapi_events"].insert_one(
                {
                    "receivedAt": datetime.now(timezone.utc),
                    "type": "whatsapp_failure",
                    "phone": None,
                    "via": "whatsapp",
                    "payload": body,
                    "error": str(exc),
                }
            )
        except Exception:
            pass

    return {"status": "ok", "processed": len(results), "results": results}
