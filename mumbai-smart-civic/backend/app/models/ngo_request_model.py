from datetime import datetime, timezone
from typing import Any, Dict
from bson import ObjectId

NGO_REQUESTS_COLLECTION = "ngo_requests"

def build_ngo_request_document(
    *,
    issue_id: str,
    issue_title: str,
    ngo_id: str,
    ngo_name: str,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "issue_id": ObjectId(issue_id),
        "issue_title": issue_title,
        "ngo_id": ObjectId(ngo_id),
        "ngo_name": ngo_name,
        "status": "pending",  # pending, approved, rejected
        "created_at": now,
        "updated_at": now,
    }

def serialize_ngo_request(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "issue_id": str(document["issue_id"]),
        "issue_title": document["issue_title"],
        "ngo_id": str(document["ngo_id"]),
        "ngo_name": document["ngo_name"],
        "status": document["status"],
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }
