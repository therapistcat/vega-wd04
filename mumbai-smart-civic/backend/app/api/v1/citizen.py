from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import re
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import require_roles
from app.models.complaint_model import (
    COMPLAINTS_COLLECTION,
    build_complaint_document,
    serialize_complaint,
)
from app.models.user_model import USERS_COLLECTION
from app.schemas.complaint_schema import (
    AnnouncementItem,
    AreaReportSearchResponse,
    AreaSummary,
    ComplaintReportResponse,
    ComplaintResponse,
    DepartmentRoute,
    ProgressOverviewResponse,
    ReporterInfo,
    SpatialAnalyticsPoint,
)
from app.services.duplicate_service import resolve_duplicate_group
from app.services.geo_service import run_st_dbscan_clustering, update_intensity_scores
from app.services.ml_service import compute_priority_score, predict_department
from app.services.complaint_service import enrich_complaint_with_detection
from app.services.spatial_service import compute_spatial_analytics


router = APIRouter(prefix="/c", tags=["citizen"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
CATEGORY_DEPARTMENT_MAP = {
    "garbage": "Solid Waste Management",
    "waste": "Solid Waste Management",
    "pothole": "Road Maintenance",
    "road": "Road Maintenance",
    "water": "Water Supply Department",
    "leak": "Water Supply Department",
    "drain": "Sewerage Operations",
    "sewage": "Sewerage Operations",
    "light": "Electrical Department",
    "electricity": "Electrical Department",
}
ANNOUNCEMENTS_COLLECTION = "announcements"
DEFAULT_CITY_COORDS = (19.0760, 72.8777)
LANDMARK_COORDINATES = {
    "andheri station": (19.119677, 72.846753),
    "andheri east": (19.1136, 72.8697),
    "andheri west": (19.1371, 72.8347),
    "dadar station": (19.0178, 72.8478),
    "bandra station": (19.0544, 72.8402),
    "kurla station": (19.0726, 72.8797),
    "chembur station": (19.0628, 72.8736),
    "churchgate": (18.9322, 72.8264),
    "cst": (18.9402, 72.8356),
}
FEED_NEWNESS_WINDOW_HOURS = 10.0
FEED_NEWNESS_BOOST_MAX = 8.0
FEED_UPVOTE_HALF_LIFE_HOURS = 20.0
FEED_OPEN_STATUS_BOOST = 0.4
FEED_IN_PROGRESS_STATUS_BOOST = 0.2
FEED_RESOLVED_STATUS_PENALTY = -0.25


def _default_announcements() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "civic-01",
            "title": "Municipal Works Progress Bulletin",
            "message": "Road restoration and drainage desilting work is in progress across identified high-priority wards. Citizens are requested to use designated diversions where notified.",
            "severity": "info",
            "created_at": now,
        },
        {
            "id": "civic-02",
            "title": "Monsoon Preparedness Advisory",
            "message": "To reduce waterlogging complaints, preventive cleaning of storm-water channels is being completed ward-wise. Please report blocked drains with image evidence for faster action.",
            "severity": "warning",
            "created_at": now - timedelta(hours=12),
        },
        {
            "id": "civic-03",
            "title": "Emergency Escalation Protocol",
            "message": "For public safety issues such as exposed electrical lines, major road collapse, or severe sewage overflow, please mark your complaint category accurately to trigger priority routing.",
            "severity": "critical",
            "created_at": now - timedelta(days=1),
        },
    ]


def _build_area_filter(
    *,
    area: str | None,
    status_filter: str | None,
    lat: float | None,
    lng: float | None,
    radius_m: int,
) -> dict:
    query: dict = {}
    if area:
        area_clean = area.strip()
        if area_clean:
            query["ward"] = {"$regex": re.escape(area_clean), "$options": "i"}

    if status_filter:
        query["status"] = status_filter

    if lat is not None and lng is not None:
        query["location"] = {
            "$geoWithin": {
                "$centerSphere": [[lng, lat], float(radius_m) / 6378137.0]
            }
        }

    return query


def _coords_from_landmark_text(text: str | None) -> tuple[float, float] | None:
    if not text:
        return None
    normalized = text.strip().lower()
    if not normalized:
        return None
    for key, coords in LANDMARK_COORDINATES.items():
        if key in normalized:
            return coords
    return None


def _resolve_complaint_coordinates(
    *,
    lat: float | None,
    lng: float | None,
    landmark: str | None,
    ward: str | None,
) -> tuple[float, float]:
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide both latitude and longitude together, or omit both",
        )
    if lat is not None and lng is not None:
        return float(lat), float(lng)

    inferred = _coords_from_landmark_text(landmark) or _coords_from_landmark_text(ward)
    if inferred:
        return inferred

    return DEFAULT_CITY_COORDS


def _as_utc_datetime(value: datetime | None) -> datetime:
    if not isinstance(value, datetime):
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _feed_rank_score(complaint: dict, now: datetime) -> float:
    created_at = _as_utc_datetime(complaint.get("created_at"))
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    upvotes_count = float(complaint.get("upvotes_count") or 0)
    priority_score = float(complaint.get("priority_score") or 0.0)

    # New issues get temporary elevation to keep feed navigation easy.
    freshness_ratio = max(0.0, 1.0 - (age_hours / FEED_NEWNESS_WINDOW_HOURS))
    newness_boost = FEED_NEWNESS_BOOST_MAX * freshness_ratio

    # Older upvotes lose influence over time so stale issues move down.
    vote_decay = math.pow(0.5, age_hours / FEED_UPVOTE_HALF_LIFE_HOURS)
    decayed_upvotes = upvotes_count * vote_decay

    status = str(complaint.get("status") or "").strip().lower()
    if status == "open":
        status_adjustment = FEED_OPEN_STATUS_BOOST
    elif status == "in progress":
        status_adjustment = FEED_IN_PROGRESS_STATUS_BOOST
    elif status == "resolved":
        status_adjustment = FEED_RESOLVED_STATUS_PENALTY
    else:
        status_adjustment = 0.0

    return newness_boost + decayed_upvotes + priority_score + status_adjustment


async def _build_report_items(
    *,
    db: AsyncIOMotorDatabase,
    docs: list[dict],
    viewer_user_id: str,
) -> list[ComplaintReportResponse]:
    user_ids = list({doc.get("user_id") for doc in docs if isinstance(doc.get("user_id"), ObjectId)})
    users = []
    if user_ids:
        users = await db[USERS_COLLECTION].find({"_id": {"$in": user_ids}}).to_list(length=len(user_ids))
    user_map = {str(user["_id"]): user for user in users}

    reports: list[ComplaintReportResponse] = []
    for doc in docs:
        serialized = serialize_complaint(doc, viewer_user_id=viewer_user_id)
        user_data = user_map.get(serialized["user_id"])
        reporter = None
        if user_data:
            reporter = ReporterInfo(
                id=str(user_data["_id"]),
                name=str(user_data.get("name") or "Unknown"),
                email=str(user_data.get("email") or ""),
                role=str(user_data.get("role") or "citizen"),
            )
        reports.append(
            ComplaintReportResponse.model_validate(
                {
                    **serialized,
                    "reporter": reporter.model_dump() if reporter else None,
                }
            )
        )
    return reports


def _resolve_extension(image: UploadFile) -> str:
    filename = (image.filename or "").strip().lower()
    suffix = Path(filename).suffix
    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return suffix
    if image.content_type == "image/png":
        return ".png"
    if image.content_type == "image/webp":
        return ".webp"
    return ".jpg"


async def _save_uploaded_image(image: UploadFile) -> str:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint image must be an image file",
        )

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Complaint image is empty")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Complaint image exceeds 8MB")

    ext = _resolve_extension(image)
    file_name = f"{uuid4().hex}{ext}"
    output_path = UPLOAD_DIR / file_name
    output_path.write_bytes(data)
    return f"/static/uploads/{file_name}"


@router.get("/departments", response_model=list[DepartmentRoute])
async def get_departments() -> list[DepartmentRoute]:
    return [
        DepartmentRoute(category=category, department=department)
        for category, department in CATEGORY_DEPARTMENT_MAP.items()
    ]


@router.get("/announcements", response_model=list[AnnouncementItem])
async def get_announcements(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[AnnouncementItem]:
    _ = current_user
    docs = await db[ANNOUNCEMENTS_COLLECTION].find({}).sort("created_at", -1).to_list(length=limit)
    if not docs:
        defaults = _default_announcements()
        return [AnnouncementItem.model_validate(item) for item in defaults]

    items: list[AnnouncementItem] = []
    for doc in docs:
        items.append(
            AnnouncementItem(
                id=str(doc.get("_id") or doc.get("id") or ""),
                title=str(doc.get("title") or "Municipal Announcement"),
                message=str(doc.get("message") or ""),
                severity=str(doc.get("severity") or "info"),
                created_at=doc.get("created_at"),
            )
        )
    return items


@router.get("/notifications", response_model=list[AnnouncementItem])
async def get_notifications(
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[AnnouncementItem]:
    announcements = await get_announcements(limit=20, current_user=current_user, db=db)
    return announcements


@router.post("/complaints", response_model=ComplaintResponse)
async def create_complaint(
    background_tasks: BackgroundTasks,
    description: str = Form(..., min_length=5, max_length=2000),
    category: str = Form(..., min_length=2, max_length=120),
    ward: str = Form(..., min_length=1, max_length=120),
    landmark: str | None = Form(default=None, max_length=200),
    lat: float | None = Form(default=None, ge=-90, le=90),
    lng: float | None = Form(default=None, ge=-180, le=180),
    image: UploadFile = File(...),
    current_user: dict = Depends(require_roles(["citizen"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ComplaintResponse:
    resolved_lat, resolved_lng = _resolve_complaint_coordinates(
        lat=lat,
        lng=lng,
        landmark=landmark,
        ward=ward,
    )
    image_url = await _save_uploaded_image(image)
    detection_enrichment = await enrich_complaint_with_detection(
        image_url=image_url,
        user_category=category,
    )
    if detection_enrichment.get("should_reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(detection_enrichment.get("reject_reason") or "Invalid complaint image"),
        )
    final_category = str(detection_enrichment["final_category"])
    department = await predict_department(description, final_category)
    duplicate_group = await resolve_duplicate_group(
        db,
        lng=resolved_lng,
        lat=resolved_lat,
    )

    complaint_doc = build_complaint_document(
        user_id=current_user["id"],
        description=description,
        category=final_category,
        ward=ward,
        lng=resolved_lng,
        lat=resolved_lat,
        priority_score=compute_priority_score(final_category),
        predicted_department=department,
        duplicate_group=duplicate_group,
        image_url=image_url,
    )
    complaint_doc["category_source"] = detection_enrichment["category_source"]
    complaint_doc["vision_detection"] = detection_enrichment["vision_detection"]
    if current_user.get("name"):
        complaint_doc["reported_by_name"] = str(current_user["name"]).strip()
    if landmark and landmark.strip():
        complaint_doc["landmark"] = landmark.strip()

    insert_result = await db[COMPLAINTS_COLLECTION].insert_one(complaint_doc)
    inserted = await db[COMPLAINTS_COLLECTION].find_one({"_id": ObjectId(insert_result.inserted_id)})
    if not inserted:
        raise HTTPException(status_code=500, detail="Failed to fetch inserted complaint")

    background_tasks.add_task(run_st_dbscan_clustering, db)
    background_tasks.add_task(update_intensity_scores, db)

    return ComplaintResponse.model_validate(serialize_complaint(inserted, viewer_user_id=current_user["id"]))


@router.get("/complaints/me", response_model=list[ComplaintResponse])
async def list_my_complaints(
    current_user: dict = Depends(require_roles(["citizen"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ComplaintResponse]:
    cursor = db[COMPLAINTS_COLLECTION].find({"user_id": ObjectId(current_user["id"])})
    complaints = await cursor.sort("created_at", -1).to_list(length=200)
    return [
        ComplaintResponse.model_validate(
            serialize_complaint(item, viewer_user_id=current_user["id"])
        )
        for item in complaints
    ]


@router.get("/my-complaints", response_model=list[ComplaintResponse])
async def list_my_complaints_alias(
    current_user: dict = Depends(require_roles(["citizen"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ComplaintResponse]:
    return await list_my_complaints(current_user=current_user, db=db)


@router.get("/complaints/feed", response_model=list[ComplaintResponse])
async def list_complaint_feed(
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ComplaintResponse]:
    cursor = db[COMPLAINTS_COLLECTION].find({})
    complaints = await cursor.to_list(length=500)
    now = datetime.now(timezone.utc)
    complaints.sort(
        key=lambda item: (
            _feed_rank_score(item, now),
            _as_utc_datetime(item.get("created_at")),
        ),
        reverse=True,
    )
    complaints = complaints[:300]
    return [
        ComplaintResponse.model_validate(
            serialize_complaint(item, viewer_user_id=current_user["id"])
        )
        for item in complaints
    ]


@router.post("/complaints/{complaint_id}/upvote", response_model=ComplaintResponse)
async def toggle_complaint_upvote(
    complaint_id: str,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ComplaintResponse:
    try:
        complaint_oid = ObjectId(complaint_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid complaint id") from exc

    user_oid = ObjectId(current_user["id"])
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": complaint_oid})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    upvoted_by = complaint.get("upvoted_by") or []
    upvotes_count = int(complaint.get("upvotes_count") or 0)

    if user_oid in upvoted_by:
        new_count = max(upvotes_count - 1, 0)
        await db[COMPLAINTS_COLLECTION].update_one(
            {"_id": complaint_oid},
            {
                "$pull": {"upvoted_by": user_oid},
                "$set": {
                    "upvotes_count": new_count,
                    "updated_at": datetime.now(timezone.utc),
                },
            },
        )
    else:
        await db[COMPLAINTS_COLLECTION].update_one(
            {"_id": complaint_oid},
            {
                "$addToSet": {"upvoted_by": user_oid},
                "$set": {"updated_at": datetime.now(timezone.utc)},
                "$inc": {"upvotes_count": 1},
            },
        )

    updated = await db[COMPLAINTS_COLLECTION].find_one({"_id": complaint_oid})
    if not updated:
        raise HTTPException(status_code=404, detail="Complaint not found")

    return ComplaintResponse.model_validate(
        serialize_complaint(updated, viewer_user_id=current_user["id"])
    )


@router.get("/spatial-analytics", response_model=list[SpatialAnalyticsPoint])
async def spatial_analytics_for_citizen(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=3000, ge=100, le=50000),
    window_hours: int = Query(default=72, ge=1, le=720),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[SpatialAnalyticsPoint]:
    _ = current_user
    points = await compute_spatial_analytics(
        db,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        window_hours=window_hours,
    )
    return [SpatialAnalyticsPoint.model_validate(point) for point in points]


@router.get("/heatmap", response_model=list[SpatialAnalyticsPoint])
async def heatmap_alias(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=3000, ge=100, le=50000),
    window_hours: int = Query(default=72, ge=1, le=720),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[SpatialAnalyticsPoint]:
    return await spatial_analytics_for_citizen(
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        window_hours=window_hours,
        current_user=current_user,
        db=db,
    )


@router.get("/reports/by-area", response_model=AreaReportSearchResponse)
async def get_reports_by_area(
    area: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status"),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=1500, ge=100, le=50000),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> AreaReportSearchResponse:
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=400, detail="Both lat and lng must be provided together")

    query = _build_area_filter(
        area=area,
        status_filter=status_filter,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
    )

    docs = await db[COMPLAINTS_COLLECTION].find(query).sort("created_at", -1).to_list(length=limit)
    reports = await _build_report_items(
        db=db,
        docs=docs,
        viewer_user_id=current_user["id"],
    )
    total_count = await db[COMPLAINTS_COLLECTION].count_documents(query)

    grouped = await db[COMPLAINTS_COLLECTION].aggregate(
        [
            {"$match": query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
    ).to_list(length=10)

    counts = {"Open": 0, "In Progress": 0, "Resolved": 0}
    for row in grouped:
        status_key = row.get("_id")
        if status_key in counts:
            counts[status_key] = int(row.get("count", 0))

    summary = AreaSummary(
        total_reports=int(total_count),
        open_count=counts["Open"],
        in_progress_count=counts["In Progress"],
        resolved_count=counts["Resolved"],
    )

    return AreaReportSearchResponse(
        area_query=area.strip() if area else None,
        summary=summary,
        reports=reports,
    )


@router.get("/reports/{complaint_id}", response_model=ComplaintReportResponse)
async def get_report_details(
    complaint_id: str,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ComplaintReportResponse:
    try:
        complaint_oid = ObjectId(complaint_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid complaint id") from exc

    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": complaint_oid})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    items = await _build_report_items(
        db=db,
        docs=[complaint],
        viewer_user_id=current_user["id"],
    )
    return items[0]


@router.get("/status/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint_status_alias(
    complaint_id: str,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ComplaintResponse:
    try:
        complaint_oid = ObjectId(complaint_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid complaint id") from exc

    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": complaint_oid})
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    serialized = serialize_complaint(complaint, viewer_user_id=current_user["id"])
    if current_user.get("role") == "citizen" and serialized["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You are not authorized to view this complaint")

    return ComplaintResponse.model_validate(serialized)


@router.get("/progress/overview", response_model=ProgressOverviewResponse)
async def progress_overview(
    area: str | None = Query(default=None, max_length=120),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int = Query(default=2500, ge=100, le=50000),
    window_hours: int = Query(default=24 * 30, ge=1, le=24 * 365),
    limit_recent: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ProgressOverviewResponse:
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=400, detail="Both lat and lng must be provided together")

    base_query = _build_area_filter(
        area=area,
        status_filter=None,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
    )
    base_query["created_at"] = {
        "$gte": datetime.now(timezone.utc) - timedelta(hours=window_hours)
    }

    total_reports = await db[COMPLAINTS_COLLECTION].count_documents(base_query)
    grouped = await db[COMPLAINTS_COLLECTION].aggregate(
        [
            {"$match": base_query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
    ).to_list(length=10)

    counts = {"Open": 0, "In Progress": 0, "Resolved": 0}
    for row in grouped:
        key = row.get("_id")
        if key in counts:
            counts[key] = int(row.get("count", 0))

    my_query = dict(base_query)
    my_query["user_id"] = ObjectId(current_user["id"])
    my_total = await db[COMPLAINTS_COLLECTION].count_documents(my_query)
    my_grouped = await db[COMPLAINTS_COLLECTION].aggregate(
        [
            {"$match": my_query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
    ).to_list(length=10)
    my_counts = {"Open": 0, "In Progress": 0, "Resolved": 0}
    for row in my_grouped:
        key = row.get("_id")
        if key in my_counts:
            my_counts[key] = int(row.get("count", 0))

    my_upvotes_agg = await db[COMPLAINTS_COLLECTION].aggregate(
        [
            {"$match": my_query},
            {"$group": {"_id": None, "sum_upvotes": {"$sum": {"$ifNull": ["$upvotes_count", 0]}}}},
        ]
    ).to_list(length=1)
    my_upvotes_received = int(my_upvotes_agg[0]["sum_upvotes"]) if my_upvotes_agg else 0

    recent_docs = await db[COMPLAINTS_COLLECTION].find(base_query).sort("created_at", -1).to_list(length=limit_recent)
    recent_reports = await _build_report_items(
        db=db,
        docs=recent_docs,
        viewer_user_id=current_user["id"],
    )

    trend_start = datetime.now(timezone.utc) - timedelta(days=6)
    trend_raw = await db[COMPLAINTS_COLLECTION].aggregate(
        [
            {
                "$match": {
                    **base_query,
                    "created_at": {"$gte": trend_start},
                }
            },
            {
                "$project": {
                    "day": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at",
                            "timezone": "Asia/Kolkata",
                        }
                    },
                    "status": "$status",
                }
            },
            {
                "$group": {
                    "_id": {"day": "$day", "status": "$status"},
                    "count": {"$sum": 1},
                }
            },
        ]
    ).to_list(length=200)

    trend_map: dict[str, dict[str, int]] = {}
    for row in trend_raw:
        day = str(row["_id"]["day"])
        status_key = str(row["_id"]["status"])
        if day not in trend_map:
            trend_map[day] = {"Open": 0, "In Progress": 0, "Resolved": 0}
        if status_key in trend_map[day]:
            trend_map[day][status_key] = int(row["count"])

    trend_points: list[dict] = []
    for i in range(7):
        day_dt = trend_start + timedelta(days=i)
        day_key = day_dt.strftime("%Y-%m-%d")
        day_counts = trend_map.get(day_key, {"Open": 0, "In Progress": 0, "Resolved": 0})
        trend_points.append(
            {
                "date": day_key,
                "open": int(day_counts["Open"]),
                "in_progress": int(day_counts["In Progress"]),
                "resolved": int(day_counts["Resolved"]),
                "total": int(day_counts["Open"] + day_counts["In Progress"] + day_counts["Resolved"]),
            }
        )

    resolution_rate = round((counts["Resolved"] / total_reports) * 100, 2) if total_reports > 0 else 0.0
    my_resolution_rate = round((my_counts["Resolved"] / my_total) * 100, 2) if my_total > 0 else 0.0

    points = (
        (my_total * 12)
        + (my_counts["In Progress"] * 8)
        + (my_counts["Resolved"] * 35)
        + (my_upvotes_received * 2)
    )
    level = int(points // 200) + 1
    next_level_points = level * 200
    badges: list[str] = []
    if my_total >= 1:
        badges.append("Civic Starter")
    if my_total >= 10:
        badges.append("Neighborhood Reporter")
    if my_total >= 25:
        badges.append("City Watch")
    if my_counts["Resolved"] >= 5:
        badges.append("Resolution Champion")
    if my_upvotes_received >= 50:
        badges.append("Community Voice")
    if my_total >= 4 and my_resolution_rate >= 50:
        badges.append("Trusted Reporter")
    if not badges:
        badges.append("New Contributor")

    status_distribution = [
        {"label": "Open", "value": int(counts["Open"])},
        {"label": "In Progress", "value": int(counts["In Progress"])},
        {"label": "Resolved", "value": int(counts["Resolved"])},
    ]

    return ProgressOverviewResponse(
        area_query=area.strip() if area else None,
        total_reports=int(total_reports),
        open_count=counts["Open"],
        in_progress_count=counts["In Progress"],
        resolved_count=counts["Resolved"],
        resolution_rate=resolution_rate,
        my_reports=int(my_total),
        my_open_count=my_counts["Open"],
        my_in_progress_count=my_counts["In Progress"],
        my_resolved_count=my_counts["Resolved"],
        my_resolution_rate=my_resolution_rate,
        points=int(points),
        level=int(level),
        next_level_points=int(next_level_points),
        badges=badges,
        status_distribution=status_distribution,
        trend_points=trend_points,
        recent_reports=recent_reports,
    )
