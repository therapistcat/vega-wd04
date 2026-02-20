from datetime import datetime, timezone
from typing import Any, Dict

from bson import ObjectId


COMPLAINTS_COLLECTION = "complaints"


def build_complaint_document(
    *,
    user_id: str,
    description: str,
    category: str,
    ward: str,
    lng: float,
    lat: float,
    priority_score: float,
    predicted_department: str,
    duplicate_group: str | None,
    image_url: str,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "user_id": ObjectId(user_id),
        "description": description,
        "category": category,
        "status": "Open",
        "ward": ward,
        "priority_score": priority_score,
        "duplicate_group": duplicate_group,
        "department": predicted_department,
        "predicted_department": predicted_department,
        "image_url": image_url,
        "fixed_image_url": None,
        "resolution_note": None,
        "resolved_by": None,
        "resolved_at": None,
        "upvotes_count": 0,
        "upvoted_by": [],
        "location": {
            "type": "Point",
            "coordinates": [lng, lat],
        },
        "created_at": now,
        "updated_at": now,
    }


def _normalize_object_id(raw: Any) -> ObjectId | None:
    if isinstance(raw, ObjectId):
        return raw
    if isinstance(raw, str):
        try:
            return ObjectId(raw)
        except Exception:
            return None
    return None


def serialize_complaint(complaint: Dict[str, Any], viewer_user_id: str | None = None) -> Dict[str, Any]:
    coordinates = complaint.get("location", {}).get("coordinates", [None, None])
    upvoted_by = complaint.get("upvoted_by") or []
    upvotes_count = int(complaint.get("upvotes_count") or 0)
    viewer_oid = _normalize_object_id(viewer_user_id)
    has_upvoted = False
    if viewer_oid is not None:
        has_upvoted = viewer_oid in upvoted_by

    return {
        "id": str(complaint["_id"]),
        "user_id": str(complaint["user_id"]),
        "reported_by_name": complaint.get("reported_by_name"),
        "description": complaint["description"],
        "landmark": complaint.get("landmark"),
        "category": complaint["category"],
        "status": complaint["status"],
        "ward": complaint["ward"],
        "priority_score": float(complaint.get("priority_score", 0.0)),
        "duplicate_group": complaint.get("duplicate_group"),
        "department": complaint.get("department") or complaint.get("predicted_department"),
        "predicted_department": complaint.get("predicted_department"),
        "image_url": complaint.get("image_url"),
        "fixed_image_url": complaint.get("fixed_image_url"),
        "resolution_note": complaint.get("resolution_note"),
        "resolved_by": complaint.get("resolved_by"),
        "resolved_at": complaint.get("resolved_at"),
        "upvotes_count": upvotes_count,
        "has_upvoted": has_upvoted,
        "location": {
            "type": "Point",
            "coordinates": [float(coordinates[0]), float(coordinates[1])],
        },
        "created_at": complaint.get("created_at"),
        "updated_at": complaint.get("updated_at"),
    }
