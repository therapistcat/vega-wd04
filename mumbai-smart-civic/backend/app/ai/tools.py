from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.complaint_model import COMPLAINTS_COLLECTION, serialize_complaint
from app.services.duplicate_service import resolve_duplicate_group
from app.services.ml_service import compute_priority_score, predict_department
from app.services.spatial_service import compute_spatial_analytics


@dataclass
class AgentToolContext:
    db: AsyncIOMotorDatabase
    current_user: dict[str, Any]
    request_lat: float | None = None
    request_lng: float | None = None


def _to_object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except Exception as exc:
        raise ValueError("Invalid ObjectId format") from exc


def _infer_category(description: str) -> str:
    text = description.lower()
    if any(token in text for token in ["pothole", "road", "crack", "footpath"]):
        return "road"
    if any(token in text for token in ["garbage", "waste", "trash", "bin"]):
        return "garbage"
    if any(token in text for token in ["water", "leak", "pipeline"]):
        return "water"
    if any(token in text for token in ["electric", "streetlight", "light", "wire"]):
        return "electricity"
    if any(token in text for token in ["sewage", "drain", "drainage", "gutter"]):
        return "sewage"
    return "general"


def _infer_coordinates_from_landmark(landmark: str) -> tuple[float, float] | None:
    text = landmark.lower()
    landmark_map: dict[str, tuple[float, float]] = {
        "andheri station": (19.119677, 72.846753),
        "andheri east": (19.1136, 72.8697),
        "andheri west": (19.1371, 72.8347),
        "dadar station": (19.0178, 72.8478),
        "bandra station": (19.0544, 72.8402),
        "kurla station": (19.0726, 72.8797),
        "chembur station": (19.0628, 72.8736),
        "cst": (18.9402, 72.8356),
        "churchgate": (18.9322, 72.8264),
        "powai": (19.1197, 72.9051),
        "goregaon": (19.1648, 72.8493),
        "thane": (19.2183, 72.9781),
    }
    for key, coords in landmark_map.items():
        if key in text:
            return coords
    return None


async def create_complaint(
    description: str,
    landmark: str,
    user_name: str,
    lat: float | None = None,
    lng: float | None = None,
    *,
    context: AgentToolContext,
) -> dict[str, Any]:
    if not description or len(description.strip()) < 5:
        raise ValueError("Complaint description must be at least 5 characters")
    if not landmark or len(landmark.strip()) < 2:
        raise ValueError("Nearest landmark is required")
    if not user_name or len(user_name.strip()) < 2:
        raise ValueError("Citizen name is required")

    resolved_lat = lat
    resolved_lng = lng
    if resolved_lat is None or resolved_lng is None:
        inferred = _infer_coordinates_from_landmark(landmark) or _infer_coordinates_from_landmark(description)
        if inferred:
            resolved_lat, resolved_lng = inferred

    if resolved_lat is None or resolved_lng is None:
        # Mumbai center fallback when only landmark text is available and geocode map misses.
        resolved_lat, resolved_lng = 19.0760, 72.8777

    if not (-90 <= float(resolved_lat) <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    if not (-180 <= float(resolved_lng) <= 180):
        raise ValueError("Longitude must be between -180 and 180")

    category = _infer_category(description)
    department = await predict_department(description=description, category=category)
    duplicate_group = await resolve_duplicate_group(
        context.db,
        lng=float(resolved_lng),
        lat=float(resolved_lat),
    )
    now = datetime.now(timezone.utc)

    complaint_doc = {
        "user_id": ObjectId(context.current_user["id"]),
        "description": description.strip(),
        "category": category,
        "status": "Open",
        "ward": "Unspecified Ward",
        "priority_score": compute_priority_score(category=category, created_at=now),
        "duplicate_group": duplicate_group,
        "department": department,
        "predicted_department": department,
        "image_url": None,
        "fixed_image_url": None,
        "resolution_note": None,
        "resolved_by": None,
        "resolved_at": None,
        "upvotes_count": 0,
        "upvoted_by": [],
        "location": {"type": "Point", "coordinates": [float(resolved_lng), float(resolved_lat)]},
        "landmark": landmark.strip(),
        "reported_by_name": user_name.strip(),
        "created_at": now,
        "updated_at": now,
        "source": "ai_agent",
    }

    insert_result = await context.db[COMPLAINTS_COLLECTION].insert_one(complaint_doc)
    stored = await context.db[COMPLAINTS_COLLECTION].find_one({"_id": insert_result.inserted_id})
    if not stored:
        raise RuntimeError("Complaint created but failed to fetch inserted record")

    serialized = serialize_complaint(stored, viewer_user_id=context.current_user["id"])
    return {
        "created": True,
        "complaint_id": serialized["id"],
        "reported_by_name": user_name.strip(),
        "landmark": landmark.strip(),
        "status": serialized["status"],
        "category": serialized["category"],
        "department": serialized.get("department"),
        "priority_score": serialized.get("priority_score"),
        "duplicate_group": serialized.get("duplicate_group"),
        "location": serialized.get("location"),
    }


async def get_my_complaints(
    user_id: str,
    *,
    context: AgentToolContext,
    limit: int = 20,
) -> list[dict[str, Any]]:
    current_user = context.current_user
    user_role = current_user.get("role")
    if user_role == "citizen" and user_id != current_user.get("id"):
        raise ValueError("Citizens can only fetch their own complaints")

    query = {"user_id": _to_object_id(user_id)}
    docs = await context.db[COMPLAINTS_COLLECTION].find(query).sort("created_at", -1).to_list(length=max(1, min(limit, 100)))
    return [
        serialize_complaint(doc, viewer_user_id=current_user.get("id"))
        for doc in docs
    ]


async def get_complaint_status(
    complaint_id: str,
    *,
    context: AgentToolContext,
) -> dict[str, Any]:
    oid = _to_object_id(complaint_id)
    complaint = await context.db[COMPLAINTS_COLLECTION].find_one({"_id": oid})
    if not complaint:
        raise ValueError("Complaint not found")

    serialized = serialize_complaint(complaint, viewer_user_id=context.current_user.get("id"))
    if context.current_user.get("role") == "citizen" and serialized["user_id"] != context.current_user.get("id"):
        raise ValueError("You are not authorized to view this complaint")

    return {
        "complaint_id": serialized["id"],
        "status": serialized["status"],
        "updated_at": serialized.get("updated_at"),
        "resolved_at": serialized.get("resolved_at"),
        "resolution_note": serialized.get("resolution_note"),
        "department": serialized.get("department"),
        "ward": serialized.get("ward"),
    }


async def get_heatmap_summary(
    *,
    context: AgentToolContext,
    lat: float | None = None,
    lng: float | None = None,
    radius_m: int = 3000,
    window_hours: int = 72,
) -> dict[str, Any]:
    center_lat = lat if lat is not None else context.request_lat
    center_lng = lng if lng is not None else context.request_lng

    points = await compute_spatial_analytics(
        context.db,
        lat=center_lat,
        lng=center_lng,
        radius_m=radius_m,
        window_hours=window_hours,
    )
    if not points:
        return {
            "hotspots_count": 0,
            "average_intensity": 0.0,
            "max_intensity": 0.0,
            "top_hotspots": [],
            "window_hours": window_hours,
            "radius_m": radius_m,
        }

    intensities = [float(point.get("intensity", 0.0)) for point in points]
    top = sorted(points, key=lambda x: x["intensity"], reverse=True)[:10]
    return {
        "hotspots_count": len(points),
        "average_intensity": round(sum(intensities) / len(intensities), 4),
        "max_intensity": round(max(intensities), 4),
        "top_hotspots": top,
        "window_hours": window_hours,
        "radius_m": radius_m,
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "create_complaint",
            "description": "Create a new civic complaint from issue description, nearest landmark, and citizen name. Coordinates are optional.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "landmark": {"type": "string"},
                    "user_name": {"type": "string"},
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                },
                "required": ["description", "landmark", "user_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_complaints",
            "description": "Fetch complaints for a user id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                },
                "required": ["user_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_complaint_status",
            "description": "Fetch status for a specific complaint id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_id": {"type": "string"},
                },
                "required": ["complaint_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_heatmap_summary",
            "description": "Get aggregated heatmap summary for complaint intensity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "radius_m": {"type": "integer", "minimum": 100, "maximum": 50000},
                    "window_hours": {"type": "integer", "minimum": 1, "maximum": 720},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


async def execute_tool_call(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    context: AgentToolContext,
) -> Any:
    if tool_name == "create_complaint":
        lat = arguments.get("lat", context.request_lat)
        lng = arguments.get("lng", context.request_lng)
        return await create_complaint(
            description=str(arguments.get("description", "")),
            landmark=str(arguments.get("landmark", "")),
            user_name=str(arguments.get("user_name", "")),
            lat=float(lat) if lat is not None else None,
            lng=float(lng) if lng is not None else None,
            context=context,
        )

    if tool_name == "get_my_complaints":
        user_id = str(arguments.get("user_id") or context.current_user.get("id") or "")
        return await get_my_complaints(user_id=user_id, context=context)

    if tool_name == "get_complaint_status":
        complaint_id = str(arguments.get("complaint_id", ""))
        return await get_complaint_status(complaint_id=complaint_id, context=context)

    if tool_name == "get_heatmap_summary":
        return await get_heatmap_summary(
            context=context,
            lat=arguments.get("lat"),
            lng=arguments.get("lng"),
            radius_m=int(arguments.get("radius_m", 3000)),
            window_hours=int(arguments.get("window_hours", 72)),
        )

    raise ValueError(f"Unsupported tool: {tool_name}")
