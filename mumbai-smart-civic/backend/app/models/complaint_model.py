from datetime import datetime, timezone
from typing import Any, Dict

from bson import ObjectId


COMPLAINTS_COLLECTION = "complaints"


def build_complaint_document(
    *,
    user_id: str | None,
    description: str,
    category: str,
    ward: str,
    lng: float = 72.8777, # Default Mumbai
    lat: float = 19.0760,
    priority_score: float = 0.0,
    predicted_department: str = "General",
    duplicate_group: str | None = None,
    image_url: str | None = None,
    source: str = "web",
    call_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    user_oid = ObjectId(user_id) if user_id else None
    return {
        "user_id": user_oid,
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
        "source": source,
        "call_metadata": call_metadata,
        "cluster_id": None,
        "is_duplicate": False,
        "ngo_request_count": 0,
        "ngo_assisting": False,
        "assistant_name": None,
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

    user_id = complaint.get("user_id")
    serialized_user_id = str(user_id) if user_id is not None else ""

    return {
        "id": str(complaint["_id"]),
        "user_id": serialized_user_id,
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
        "source": complaint.get("source", "web"),
        "call_metadata": complaint.get("call_metadata"),
        "cluster_id": complaint.get("cluster_id"),
        "is_duplicate": bool(complaint.get("is_duplicate", False)),
        "ngo_request_count": int(complaint.get("ngo_request_count", 0)),
        "ngo_assisting": bool(complaint.get("ngo_assisting", False)),
        "assistant_name": complaint.get("assistant_name"),
        "created_at": complaint.get("created_at"),
        "updated_at": complaint.get("updated_at"),
    }
