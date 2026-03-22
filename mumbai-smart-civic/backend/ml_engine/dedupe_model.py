from __future__ import annotations

from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt


EARTH_RADIUS_METERS = 6371000.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(max(1e-12, 1 - a)))
    return EARTH_RADIUS_METERS * c


def is_duplicate_candidate(
    *,
    new_lat: float,
    new_lng: float,
    existing_lat: float,
    existing_lng: float,
    existing_created_at: datetime | None,
    radius_meters: int,
    window_hours: int,
) -> bool:
    distance = _haversine_m(new_lat, new_lng, existing_lat, existing_lng)
    if distance > float(radius_meters):
        return False

    if not isinstance(existing_created_at, datetime):
        return True
    if existing_created_at.tzinfo is None:
        existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)
    age_h = (datetime.now(timezone.utc) - existing_created_at).total_seconds() / 3600.0
    return age_h <= float(window_hours)

