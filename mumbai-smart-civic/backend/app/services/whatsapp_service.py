from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.services.call_service import parse_call_to_complaint
from app.services.complaint_ingestion_service import create_ingested_complaint
from app.services.detection_service import get_detection_service
from app.services.whatsapp_session_service import (
    STATE_AWAITING_COMPLAINT,
    STATE_AWAITING_IMAGE,
    STATE_AWAITING_LOCATION,
    STATE_DONE,
    STATE_IDLE,
    STATE_PROCESSING,
    complete_session,
    get_session,
    refresh_session,
    reset_session,
    start_session,
    update_session,
)


WHATSAPP_LOG_COLLECTION = "vapi_events"
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

WELCOME_TEXT = "Please describe your issue"
ASK_IMAGE_TEXT = "Upload an image"
ASK_LOCATION_TEXT = "Share location"
PROCESSING_TEXT = "Location received. Filing your complaint now..."
SUCCESS_TEXT = "Complaint registered successfully"
RESTART_TEXT = "Something went wrong. Please send hi to try again."


async def log_whatsapp_event(
    db: AsyncIOMotorDatabase,
    *,
    message_type: str,
    phone: str | None,
    payload: dict[str, Any],
    error: str | None = None,
) -> None:
    await db[WHATSAPP_LOG_COLLECTION].insert_one(
        {
            "receivedAt": datetime.now(timezone.utc),
            "type": message_type,
            "phone": phone,
            "phone_number": phone,
            "via": "whatsapp",
            "payload": payload,
            **({"error": error} if error else {}),
        }
    )


async def _chat_completion(messages: list[dict[str, Any]]) -> str:
    if not settings.openai_api_key:
        return ""
    endpoint = f"{settings.openai_api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.ai_agent_model,
        "temperature": 0.0,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=settings.ai_agent_timeout_seconds) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def detect_and_translate_text(text: str) -> dict[str, str]:
    clean_text = text.strip()
    if not clean_text:
        return {"language": "unknown", "english_text": ""}
    if not settings.openai_api_key:
        return {"language": "unknown", "english_text": clean_text}
    content = await _chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "Detect the language of the user text and translate it to English. "
                    "Return JSON with keys language and english_text."
                ),
            },
            {"role": "user", "content": clean_text},
        ]
    )
    try:
        parsed = json.loads(content)
        return {
            "language": str(parsed.get("language") or "unknown"),
            "english_text": str(parsed.get("english_text") or clean_text).strip(),
        }
    except Exception:
        return {"language": "unknown", "english_text": clean_text}


async def transcribe_media(media_bytes: bytes, mime_type: str | None, filename: str) -> str:
    if not settings.openai_api_key:
        return "WhatsApp media complaint received."
    endpoint = f"{settings.openai_api_base.rstrip('/')}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    files = {
        "file": (filename, media_bytes, mime_type or "application/octet-stream"),
        "model": (None, "whisper-1"),
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(endpoint, headers=headers, files=files)
        response.raise_for_status()
        data = response.json()
        return str(data.get("text") or "").strip()


def _suffix_from_mime(mime_type: str | None, default_ext: str) -> str:
    mime = str(mime_type or "").lower()
    if "png" in mime:
        return ".png"
    if "webp" in mime:
        return ".webp"
    if "jpeg" in mime or "jpg" in mime:
        return ".jpg"
    if "ogg" in mime:
        return ".ogg"
    if "mpeg" in mime or "mp3" in mime:
        return ".mp3"
    if "mp4" in mime:
        return ".mp4"
    if "mov" in mime:
        return ".mov"
    return default_ext


def save_media_bytes(raw: bytes, suffix: str) -> str:
    file_name = f"{uuid4().hex}{suffix}"
    output = UPLOAD_DIR / file_name
    output.write_bytes(raw)
    return f"/static/uploads/{file_name}"


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in str(phone or "") if ch.isdigit())


async def send_whatsapp_reply(phone: str, text: str) -> None:
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        raise ValueError("Missing WhatsApp phone number")
    if not settings.whatsapp_access_token:
        raise ValueError("WHATSAPP_ACCESS_TOKEN is not configured")
    if not settings.whatsapp_phone_number_id:
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID is not configured")

    payload = {
        "messaging_product": "whatsapp",
        "to": normalized_phone,
        "type": "text",
        "text": {"body": text},
    }
    endpoint = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    print("SENDING TO:", normalized_phone)
    print("MESSAGE:", text)
    print(f"TO: {normalized_phone} | RESPONSE: {text}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
        )
        print("META RESPONSE STATUS:", response.status_code)
        print("META RESPONSE BODY:", response.text)
        if response.status_code != 200:
            raise ValueError(f"Meta send failed ({response.status_code}): {response.text}")


def _message_type(message: dict[str, Any]) -> str:
    return str(message.get("type") or "unknown")


def _extract_text_body(message: dict[str, Any]) -> str:
    return str((message.get("text") or {}).get("body") or "").strip()


def _media_payload(message: dict[str, Any], media_type: str) -> tuple[bytes, str | None]:
    payload = message.get(media_type) or {}
    media_bytes = payload.get("bytes")
    if not isinstance(media_bytes, (bytes, bytearray)):
        raise ValueError(f"Missing media bytes for {media_type}")
    return bytes(media_bytes), payload.get("mime_type")


async def _extract_complaint_text(message: dict[str, Any]) -> tuple[str, str, str]:
    message_type = _message_type(message)
    if message_type == "text":
        original = _extract_text_body(message)
    elif message_type in {"audio", "video"}:
        media_bytes, mime_type = _media_payload(message, message_type)
        original = await transcribe_media(
            media_bytes,
            mime_type,
            f"{uuid4().hex}{_suffix_from_mime(mime_type, '.bin')}",
        )
    else:
        raise ValueError("Please describe your complaint using text, voice, or video.")

    translated = await detect_and_translate_text(original)
    return original, translated["english_text"], translated["language"]


async def _extract_image_data(message: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str]:
    if _message_type(message) != "image":
        raise ValueError("Please send an image of the issue.")
    image_bytes, mime_type = _media_payload(message, "image")
    image_path = save_media_bytes(image_bytes, _suffix_from_mime(mime_type, ".jpg"))
    detections = await get_detection_service().detect_bytes(image_bytes)
    top = detections[0] if detections else {}
    top_class = str(top.get("class") or "general").lower()
    category = "road" if top_class == "pothole" else top_class
    return image_path, detections, category or "general"


def _extract_location(message: dict[str, Any]) -> dict[str, float]:
    if _message_type(message) != "location":
        raise ValueError("Please share the issue location using WhatsApp location sharing.")
    location = message.get("location") or {}
    lat = location.get("latitude")
    lng = location.get("longitude")
    if lat is None or lng is None:
        raise ValueError("Location data is missing. Please send the location again.")
    return {"latitude": float(lat), "longitude": float(lng)}


async def _create_complaint_from_session(
    db: AsyncIOMotorDatabase,
    background_tasks: BackgroundTasks,
    *,
    phone: str,
    session: dict[str, Any],
) -> str:
    complaint_text = str(session.get("complaint_text") or "").strip()
    parsed = parse_call_to_complaint(complaint_text)
    location = session.get("location") or {}
    lat = location.get("latitude")
    lng = location.get("longitude")
    image_path = str(session.get("image_path") or "").strip() or None
    detected_category = str(session.get("detected_category") or "").strip()
    category = detected_category if detected_category and detected_category != "general" else parsed["category"]
    created = await create_ingested_complaint(
        db,
        background_tasks=background_tasks,
        description=parsed.get("description") or complaint_text,
        category=category or parsed["category"],
        ward=parsed.get("ward") or "A Ward",
        reporter_name=f"WhatsApp {phone}",
        landmark=parsed.get("landmark"),
        lat=float(lat) if lat is not None else None,
        lng=float(lng) if lng is not None else None,
        image_url=image_path,
        source="whatsapp",
        cluster_location=parsed.get("location") or parsed.get("landmark") or parsed.get("ward") or "Mumbai",
        extra_fields={
            "phone_number": phone,
            "via": "whatsapp",
            "source_language": session.get("source_language") or "unknown",
            "source_text": session.get("complaint_text_original") or complaint_text,
            "translated_text": complaint_text,
            "vision_detection_whatsapp": session.get("vision_detection_whatsapp") or [],
            "whatsapp_session_state": STATE_DONE,
        },
        actor={"id": phone, "name": f"WhatsApp {phone}", "role": "citizen"},
    )
    return str(created["_id"])


async def _reply_and_result(*, phone: str, message: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    print("Sending reply:", phone, message)
    try:
        await send_whatsapp_reply(phone, message)
    except Exception as exc:
        print(f"[whatsapp] reply send failed for {phone}: {exc}")
        raise
    return {"success": True, "reply": message, **(result or {})}


async def handle_incoming_message(
    db: AsyncIOMotorDatabase,
    background_tasks: BackgroundTasks,
    *,
    phone: str,
    message: dict[str, Any],
    raw_payload: dict[str, Any],
) -> dict[str, Any]:
    message_type = _message_type(message)
    print(f"FROM: {phone} | TYPE: {message_type}")
    await log_whatsapp_event(db, message_type=message_type, phone=phone, payload=raw_payload)
    message_text = _extract_text_body(message).strip().lower() if message_type == "text" else ""

    session = await get_session(db, phone)
    if session and session.get("state") in {STATE_DONE, STATE_IDLE}:
        await reset_session(db, phone)
        session = None

    if session is None or message_text in {"hi", "hello", "start", "restart"}:
        await start_session(db, phone)
        print("Sending reply:", phone, WELCOME_TEXT)
        await send_whatsapp_reply(phone, WELCOME_TEXT)
        return {
            "success": True,
            "phone": phone,
            "type": message_type,
            "state": STATE_AWAITING_COMPLAINT,
            "reply": WELCOME_TEXT,
        }

    session = await refresh_session(db, phone)
    state = str(session.get("state") or STATE_AWAITING_COMPLAINT)

    try:
        if state == STATE_AWAITING_COMPLAINT:
            original_text, english_text, source_language = await _extract_complaint_text(message)
            await update_session(
                db,
                phone,
                state=STATE_AWAITING_IMAGE,
                fields={
                    "complaint_text": english_text,
                    "complaint_text_original": original_text,
                    "source_language": source_language,
                },
            )
            return await _reply_and_result(
                phone=phone,
                message=ASK_IMAGE_TEXT,
                result={"phone": phone, "type": message_type, "state": STATE_AWAITING_IMAGE},
            )

        if state == STATE_AWAITING_IMAGE:
            image_path, detections, category = await _extract_image_data(message)
            await update_session(
                db,
                phone,
                state=STATE_AWAITING_LOCATION,
                fields={
                    "image_path": image_path,
                    "detected_category": category,
                    "vision_detection_whatsapp": detections,
                },
            )
            return await _reply_and_result(
                phone=phone,
                message=ASK_LOCATION_TEXT,
                result={"phone": phone, "type": message_type, "state": STATE_AWAITING_LOCATION},
            )

        if state == STATE_AWAITING_LOCATION:
            location = _extract_location(message)
            processing_session = await update_session(
                db,
                phone,
                state=STATE_PROCESSING,
                fields={"location": location},
            )
            print("Sending reply:", phone, PROCESSING_TEXT)
            await send_whatsapp_reply(phone, PROCESSING_TEXT)
            complaint_id = await _create_complaint_from_session(
                db,
                background_tasks,
                phone=phone,
                session=processing_session,
            )
            await complete_session(db, phone, complaint_id=complaint_id)
            final_text = f"{SUCCESS_TEXT}. ID: {complaint_id}"
            print("Sending reply:", phone, final_text)
            await send_whatsapp_reply(phone, final_text)
            return {
                "success": True,
                "phone": phone,
                "type": message_type,
                "state": STATE_IDLE,
                "complaint_id": complaint_id,
                "reply": final_text,
            }

        await start_session(db, phone)
        print("Sending reply:", phone, WELCOME_TEXT)
        await send_whatsapp_reply(phone, WELCOME_TEXT)
        return {
            "success": True,
            "phone": phone,
            "type": message_type,
            "state": STATE_AWAITING_COMPLAINT,
            "reply": WELCOME_TEXT,
        }
    except Exception as exc:
        error_message = str(exc)
        print(f"[whatsapp] processing failed for {phone}: {error_message}")
        await log_whatsapp_event(
            db,
            message_type="whatsapp_failure",
            phone=phone,
            payload=raw_payload,
            error=error_message,
        )
        await reset_session(db, phone)
        try:
            print("Sending reply:", phone, f"{error_message} Send hi to try again.")
            await send_whatsapp_reply(phone, f"{error_message} Send hi to try again.")
        except Exception:
            pass
        return {
            "success": False,
            "phone": phone,
            "type": message_type,
            "error": error_message,
            "reply": RESTART_TEXT,
        }
