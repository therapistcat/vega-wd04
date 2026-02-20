from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ComplaintStatus = Literal["Open", "In Progress", "Resolved"]


class LocationInput(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ComplaintCreateRequest(BaseModel):
    description: str = Field(min_length=5, max_length=2000)
    category: str = Field(min_length=2, max_length=120)
    ward: str = Field(min_length=1, max_length=120)
    location: LocationInput


class ComplaintResponse(BaseModel):
    id: str
    user_id: str
    reported_by_name: str | None = None
    description: str
    landmark: str | None = None
    category: str
    status: ComplaintStatus
    ward: str
    priority_score: float
    duplicate_group: str | None = None
    department: str | None = None
    predicted_department: str | None = None
    image_url: str | None = None
    fixed_image_url: str | None = None
    resolution_note: str | None = None
    resolved_by: dict | None = None
    resolved_at: datetime | None = None
    upvotes_count: int = Field(default=0, ge=0)
    has_upvoted: bool = False
    location: dict
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReporterInfo(BaseModel):
    id: str
    name: str
    email: str
    role: str


class ComplaintReportResponse(ComplaintResponse):
    reporter: ReporterInfo | None = None


class AreaSummary(BaseModel):
    total_reports: int = 0
    open_count: int = 0
    in_progress_count: int = 0
    resolved_count: int = 0


class AreaReportSearchResponse(BaseModel):
    area_query: str | None = None
    summary: AreaSummary
    reports: list[ComplaintReportResponse]


class ProgressOverviewResponse(BaseModel):
    area_query: str | None = None
    total_reports: int = 0
    open_count: int = 0
    in_progress_count: int = 0
    resolved_count: int = 0
    resolution_rate: float = 0.0
    my_reports: int = 0
    my_open_count: int = 0
    my_in_progress_count: int = 0
    my_resolved_count: int = 0
    my_resolution_rate: float = 0.0
    points: int = 0
    level: int = 1
    next_level_points: int = 200
    badges: list[str] = []
    status_distribution: list[dict] = []
    trend_points: list[dict] = []
    recent_reports: list[ComplaintReportResponse] = []


class AnnouncementItem(BaseModel):
    id: str
    title: str
    message: str
    severity: Literal["info", "warning", "critical"] = "info"
    created_at: datetime | None = None


class ComplaintStatusUpdateRequest(BaseModel):
    status: ComplaintStatus


class SpatialAnalyticsPoint(BaseModel):
    lat: float
    lng: float
    intensity: float = Field(ge=0.0, le=1.0)


class DepartmentRoute(BaseModel):
    category: str
    department: str
