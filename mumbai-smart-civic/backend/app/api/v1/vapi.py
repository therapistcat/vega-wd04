from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import verify_vapi_token
from app.models.complaint_model import COMPLAINTS_COLLECTION, build_complaint_document
from app.services.call_service import parse_call_to_complaint
from app.services.clustering_service import process_issue as cluster_process_issue

router = APIRouter(prefix="/vapi", tags=["vapi"])


@router.get("/ping")
async def vapi_ping(_: bool = Depends(verify_vapi_token)) -> dict[str, Any]:
    return {"ok": True, "service": "vapi", "authenticated": True}


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict[str, Any]:
    try:
        # 1. AUTH HANDLING
        auth = request.headers.get("Authorization")
        if not auth:
            print("WARNING: Missing Authorization header")
        
        # 2. SAFE PAYLOAD HANDLING
        try:
            payload_data = await request.json()
            if not isinstance(payload_data, dict):
                payload_data = {}
        except Exception:
            payload_data = {}
        print("WEBHOOK RECEIVED:", payload_data)

        now = datetime.now(timezone.utc)
        
        # 3. EXTRACT IMPORTANT FIELDS
        call_object = payload_data.get("call")
        if not isinstance(call_object, dict):
            call_object = {}
            
        message_object = payload_data.get("message")
        if not isinstance(message_object, dict):
            message_object = {}
            
        message_call_object = message_object.get("call")
        if not isinstance(message_call_object, dict):
            message_call_object = {}
        
        call_id_val = call_object.get("id")
        if not call_id_val:
            call_id_val = message_call_object.get("id")
            
        call_id = str(call_id_val) if call_id_val else ""

        event_type_val = payload_data.get("type") or payload_data.get("event")
        if not event_type_val:
            event_type_val = message_object.get("type")
            
        event_type = str(event_type_val) if event_type_val else "unknown"

        await db["vapi_events"].insert_one(
            {
                "call_id": call_id or None,
                "event_type": event_type,
                "payload": payload_data,
                "created_at": now,
            }
        )

        transcript_val = payload_data.get("transcript")
        if not transcript_val:
            transcript_val = message_object.get("transcript")
        transcript = str(transcript_val) if transcript_val else ""

        caller_object = payload_data.get("caller")
        if not isinstance(caller_object, dict):
            caller_object = message_call_object.get("customer")
            if not isinstance(caller_object, dict):
                caller_object = {}
        
        phone_number = caller_object.get("number")
            
        duration = payload_data.get("duration")
        if not duration:
            duration = message_object.get("duration")

        if transcript and call_id:
            # 4. EXTRACT COMPLAINT SUMMARY
            if "Complaint Summary:" in transcript:
                summary = transcript.split("Complaint Summary:")[-1].strip()
            else:
                summary = transcript

            # 7. PREVENT DUPLICATES
            existing = await db[COMPLAINTS_COLLECTION].find_one({"call_metadata.call_id": call_id})
            if not existing:
                # 5. CREATE COMPLAINT
                title = summary[:80] if summary else "Voice Complaint"
                
                metadata = {
                    "phone_number": phone_number,
                    "call_id": call_id,
                    "duration": duration,
                    "transcript": transcript
                }
                
                complaint_doc = build_complaint_document(
                    user_id=None,
                    description=summary,
                    category="general", # Per objective
                    ward="Unknown Ward",
                    source="call",
                    call_metadata=metadata
                )
                # Overwrite defaults to match objective exactly
                complaint_doc["title"] = title
                complaint_doc["department"] = "general"
                complaint_doc["status"] = "Open"
                
                # 6. STORE IN MONGODB
                await db[COMPLAINTS_COLLECTION].insert_one(complaint_doc)

                # Cluster the new complaint
                try:
                    cluster_result = await cluster_process_issue(
                        db,
                        category="general",
                        location="Unknown Ward",
                        description=summary,
                        complaint_id=str(complaint_doc.get("_id", "")),
                        source="call",
                    )
                    await db[COMPLAINTS_COLLECTION].update_one(
                        {"call_metadata.call_id": call_id},
                        {"$set": {
                            "cluster_id": cluster_result["cluster_id"],
                            "is_duplicate": cluster_result["is_duplicate"],
                        }},
                    )
                except Exception as ce:
                    print(f"[clustering/vapi] error: {ce}")

        # 8. ALWAYS RETURN RESPONSE
        return {"ok": True, "message": "Webhook processed"}

    except Exception as e:
        # 9. FULL ERROR SAFETY
        print("ERROR:", str(e))
        return {"ok": False}
