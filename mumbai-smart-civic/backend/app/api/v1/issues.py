from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import require_roles
from app.models.complaint_model import COMPLAINTS_COLLECTION
from app.schemas.complaint_schema import NearbyIssueResponse


router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("/nearby", response_model=list[NearbyIssueResponse])
async def get_nearby_issues(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(default=2000, ge=100, le=10000),
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin", "ngo"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> list[NearbyIssueResponse]:
    _ = current_user

    try:
        docs = await db[COMPLAINTS_COLLECTION].aggregate(
            [
                {
                    "$geoNear": {
                        "near": {"type": "Point", "coordinates": [lng, lat]},
                        "distanceField": "distance_m",
                        "maxDistance": radius,
                        "spherical": True,
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "description": 1,
                        "status": 1,
                        "progress_status": 1,
                        "assigned_ngo_name": 1,
                        "priority_score": {"$ifNull": ["$priority_score", 0]},
                        "ward": 1,
                        "category": 1,
                        "created_at": 1,
                        "updated_at": 1,
                        "distance_m": 1,
                        "location": 1,
                    }
                },
                {"$sort": {"distance_m": 1, "priority_score": -1, "updated_at": -1}},
                {"$limit": 250},
            ]
        ).to_list(length=250)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to fetch nearby issues") from exc

    response: list[NearbyIssueResponse] = []
    for item in docs:
        coordinates = item.get("location", {}).get("coordinates") or [None, None]
        longitude = coordinates[0]
        latitude = coordinates[1]
        if longitude is None or latitude is None:
            continue

        progress_status = str(item.get("progress_status") or "Pending")
        status = str(item.get("status") or "Open")
        display_status = progress_status
        if display_status == "Pending" and status == "Resolved":
            display_status = "Resolved"
        elif display_status == "Pending" and status == "In Progress":
            display_status = "In Progress"

        response.append(
            NearbyIssueResponse(
                id=str(item["_id"]),
                description=str(item.get("description") or ""),
                status=status,
                progress_status=progress_status,
                display_status=display_status,
                latitude=float(latitude),
                longitude=float(longitude),
                distance_m=float(item.get("distance_m") or 0.0),
                assigned_ngo_name=item.get("assigned_ngo_name"),
                priority_score=float(item.get("priority_score") or 0.0),
                ward=item.get("ward"),
                category=item.get("category"),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
            )
        )

    return response
