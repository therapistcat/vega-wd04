from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.database import get_database
from app.core.security import verify_vapi_token
from app.models.complaint_model import COMPLAINTS_COLLECTION, build_complaint_document
from app.services.call_service import parse_call_to_complaint
from app.services.clustering_service import process_issue as cluster_process_issue
from app.services.geo_service import run_st_dbscan_clustering, update_intensity_scores
from app.services.ml_service import compute_priority_score, predict_department
from app.services.whatsapp_service import handle_incoming_message

router = APIRouter(prefix="/vapi", tags=["vapi"])


def _nested_get(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_call_id(body: dict[str, Any]) -> str | None:
    candidates = [
        _nested_get(body, "call", "id"),
        _nested_get(body, "message", "call", "id"),
        _nested_get(body, "message", "callId"),
        body.get("callId"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_event_type(body: dict[str, Any]) -> str:
    candidates = [
        body.get("type"),
        _nested_get(body, "message", "type"),
        _nested_get(body, "message", "eventType"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return "unknown"


def _extract_summary(body: dict[str, Any]) -> str | None:
    candidates = [
        _nested_get(body, "message", "analysis", "summary"),
        _nested_get(body, "analysis", "summary"),
        body.get("summary"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_transcript(body: dict[str, Any]) -> str | None:
    candidates = [
        body.get("transcript"),
        _nested_get(body, "message", "transcript"),
        _nested_get(body, "message", "artifact", "transcript"),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _is_meta_whatsapp_payload(body: dict[str, Any]) -> bool:
    if not isinstance(body, dict):
        return False
    entries = body.get("entry")
    return isinstance(entries, list) and len(entries) > 0


def _normalize_phone(phone: Any) -> str:
    return "".join(ch for ch in str(phone or "") if ch.isdigit())


async def _download_meta_media(media_id: str) -> tuple[bytes, str | None]:
    if not settings.whatsapp_access_token:
        raise ValueError("WHATSAPP_ACCESS_TOKEN is not configured")

    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        meta_res = await client.get(
            f"https://graph.facebook.com/{settings.whatsapp_api_version}/{media_id}",
            headers=headers,
        )
        meta_res.raise_for_status()
        meta = meta_res.json()
        media_url = meta.get("url")
        if not media_url:
            raise ValueError("Media URL missing from Meta response")
        mime_type = meta.get("mime_type")
        file_res = await client.get(media_url, headers=headers)
        file_res.raise_for_status()
        return file_res.content, mime_type


async def _normalize_meta_message(message: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    phone = _normalize_phone(message.get("from"))
    if not phone:
        raise ValueError("Missing phone number")

    message_type = str(message.get("type") or "").strip().lower()
    if message_type == "text":
        text_body = str((message.get("text") or {}).get("body") or "").strip()
        print(f"FROM: {phone} | TYPE: text | MESSAGE: {text_body}")
        return phone, {"type": "text", "text": {"body": text_body}}

    if message_type == "image":
        image = message.get("image") or {}
        media_id = str(image.get("id") or "").strip()
        media_bytes, mime_type = await _download_meta_media(media_id)
        print(f"FROM: {phone} | TYPE: image | MESSAGE: [image]")
        return phone, {"type": "image", "image": {"bytes": media_bytes, "mime_type": mime_type}}

    if message_type == "audio":
        audio = message.get("audio") or {}
        media_id = str(audio.get("id") or "").strip()
        media_bytes, mime_type = await _download_meta_media(media_id)
        print(f"FROM: {phone} | TYPE: audio | MESSAGE: [audio]")
        return phone, {"type": "audio", "audio": {"bytes": media_bytes, "mime_type": mime_type}}

    if message_type == "location":
        location = message.get("location") or {}
        print(f"FROM: {phone} | TYPE: location | MESSAGE: [location]")
        return phone, {
            "type": "location",
            "location": {
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            },
        }

    raise ValueError(f"Unsupported WhatsApp message type: {message_type or 'unknown'}")


async def _handle_meta_whatsapp_webhook(
    body: dict[str, Any],
    *,
    db: AsyncIOMotorDatabase,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    entries = body.get("entry") or []
    for entry in entries:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            statuses = value.get("statuses") or []

            for status in statuses:
                await db["vapi_events"].insert_one(
                    {
                        "receivedAt": datetime.now(timezone.utc),
                        "type": "whatsapp_status",
                        "phone": _normalize_phone(status.get("recipient_id")),
                        "phone_number": _normalize_phone(status.get("recipient_id")),
                        "via": "whatsapp",
                        "payload": status,
                    }
                )

            for message in messages:
                phone, normalized_message = await _normalize_meta_message(message)
                result = await handle_incoming_message(
                    db,
                    background_tasks,
                    phone=phone,
                    message=normalized_message,
                    raw_payload=message,
                )
                results.append(result)

            if not messages and not statuses:
                await db["vapi_events"].insert_one(
                    {
                        "receivedAt": datetime.now(timezone.utc),
                        "type": "whatsapp_raw",
                        "phone": None,
                        "phone_number": None,
                        "via": "whatsapp",
                        "payload": value,
                    }
                )

    return {"status": "ok", "processed": len(results), "results": results}


@router.get("/ping")
async def vapi_ping(_: bool = Depends(verify_vapi_token)) -> dict[str, Any]:
    return {"ok": True, "service": "vapi", "authenticated": True}


@router.get("/webhook")
async def vapi_meta_verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Any:
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else (hub_challenge or "")
    return {"status": "verification_failed"}


@router.post("/webhook")
async def vapi_webhook(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database),
    body: dict[str, Any] = Body(
        default_factory=dict,
        example={
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "918928411910",
                                        "id": "wamid.test123",
                                        "timestamp": "1774800000",
                                        "type": "text",
                                        "text": {"body": "hi"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    ),
) -> dict[str, Any]:
    print("META WEBHOOK HIT")

    if _is_meta_whatsapp_payload(body):
        try:
            return await _handle_meta_whatsapp_webhook(
                body,
                db=db,
                background_tasks=background_tasks,
            )
        except Exception as exc:
            print(f"[meta-whatsapp] webhook failure: {exc}")
            try:
                await db["vapi_events"].insert_one(
                    {
                        "receivedAt": datetime.now(timezone.utc),
                        "type": "whatsapp_failure",
                        "phone": None,
                        "phone_number": None,
                        "via": "whatsapp",
                        "payload": body,
                        "error": str(exc),
                    }
                )
            except Exception:
                pass
            return {"status": "ok", "error": str(exc)}

    try:
        call_id = _extract_call_id(body)
        event_type = _extract_event_type(body)
        transcript = _extract_transcript(body)
        summary = _extract_summary(body)

        event_doc = {
            "receivedAt": datetime.now(timezone.utc),
            "callId": call_id,
            "type": event_type,
            "payload": body,
        }
        await db["vapi_events"].insert_one(event_doc)

        complaint_created = False
        complaint_id: str | None = None

        if event_type == "end-of-call-report" and call_id:
            existing = await db[COMPLAINTS_COLLECTION].find_one(
                {"call_metadata.call_id": call_id},
                {"_id": 1},
            )
            if existing:
                complaint_id = str(existing["_id"])
            else:
                raw_call_text = (summary or transcript or "").strip()
                if raw_call_text:
                    parsed = parse_call_to_complaint(summary or "", transcript=transcript)
                    complaint_text = parsed.get("description") or parsed.get("summary") or ""
                    department = await predict_department(
                        complaint_text,
                        parsed["category"],
                    )
                    phone_number = (
                        _nested_get(body, "call", "customer", "number")
                        or _nested_get(body, "message", "call", "customer", "number")
                        or "unknown"
                    )
                    duration = (
                        _nested_get(body, "call", "duration")
                        or _nested_get(body, "message", "call", "duration")
                    )

                    complaint_doc = build_complaint_document(
                        user_id=None,
                        description=complaint_text,
                        category=parsed["category"],
                        ward=parsed["ward"],
                        priority_score=compute_priority_score(parsed["category"]),
                        predicted_department=department,
                        source="call",
                        call_metadata={
                            "call_id": call_id,
                            "event_type": event_type,
                            "phone_number": phone_number,
                            "duration": duration,
                            "summary": parsed.get("summary"),
                            "problem": parsed.get("problem"),
                            "location_text": parsed.get("location"),
                            "details": parsed.get("details"),
                            "transcript": transcript,
                        },
                    )
                    complaint_doc["reported_by_name"] = "Voice Hotline"
                    complaint_doc["title"] = parsed["title"]
                    complaint_doc["is_verified"] = False
                    if parsed.get("landmark"):
                        complaint_doc["landmark"] = parsed["landmark"]

                    insert_result = await db[COMPLAINTS_COLLECTION].insert_one(complaint_doc)
                    complaint_id = str(insert_result.inserted_id)

                    cluster_result = await cluster_process_issue(
                        db,
                        category=parsed["category"],
                        location=parsed.get("location") or parsed["ward"],
                        description=complaint_text,
                        complaint_id=complaint_id,
                        source="call",
                    )
                    await db[COMPLAINTS_COLLECTION].update_one(
                        {"_id": insert_result.inserted_id},
                        {
                            "$set": {
                                "cluster_id": cluster_result["cluster_id"],
                                "is_duplicate": cluster_result["is_duplicate"],
                                "updated_at": datetime.now(timezone.utc),
                            }
                        },
                    )
                    complaint_created = True
                    background_tasks.add_task(run_st_dbscan_clustering, db)
                    background_tasks.add_task(update_intensity_scores, db)

        return {
            "status": "success",
            "callId": call_id,
            "eventType": event_type,
            "complaintCreated": complaint_created,
            "complaintId": complaint_id,
        }
    except Exception as exc:
        print(f"[vapi-webhook] failure: {exc}")
        try:
            await db["vapi_events"].insert_one(
                {
                    "receivedAt": datetime.now(timezone.utc),
                    "type": "vapi_webhook_failure",
                    "payload": body,
                    "error": str(exc),
                }
            )
        except Exception:
            pass
        return {"status": "ok", "error": str(exc)}
