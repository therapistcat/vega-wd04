from __future__ import annotations

from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt
from typing import Any


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return r * c


def _hours_between(a: datetime, b: datetime) -> float:
    a_utc = a if a.tzinfo else a.replace(tzinfo=timezone.utc)
    b_utc = b if b.tzinfo else b.replace(tzinfo=timezone.utc)
    return abs((a_utc - b_utc).total_seconds()) / 3600


def st_dbscan_cluster(
    complaints: list[dict[str, Any]],
    *,
    spatial_eps_meters: float,
    temporal_eps_hours: float,
    min_samples: int,
) -> dict[str, str]:
    if len(complaints) < min_samples:
        return {}

    points: list[dict[str, Any]] = []
    for complaint in complaints:
        coords = complaint.get("location", {}).get("coordinates", [None, None])
        if len(coords) != 2:
            continue
        points.append(
            {
                "id": str(complaint["_id"]),
                "lng": float(coords[0]),
                "lat": float(coords[1]),
                "created_at": complaint.get("created_at") or datetime.now(timezone.utc),
            }
        )

    cluster_assignments: dict[str, str] = {}
    visited: set[str] = set()
    cluster_id = 0

    def neighbors(seed: dict[str, Any]) -> list[dict[str, Any]]:
        result = []
        for candidate in points:
            spatial_distance = _haversine_meters(
                seed["lat"], seed["lng"], candidate["lat"], candidate["lng"]
            )
            temporal_distance = _hours_between(seed["created_at"], candidate["created_at"])
            if spatial_distance <= spatial_eps_meters and temporal_distance <= temporal_eps_hours:
                result.append(candidate)
        return result

    for point in points:
        if point["id"] in visited:
            continue
        visited.add(point["id"])

        seed_neighbors = neighbors(point)
        if len(seed_neighbors) < min_samples:
            continue

        cluster_id += 1
        label = f"stc-{cluster_id}"

        queue = seed_neighbors[:]
        while queue:
            current = queue.pop(0)
            if current["id"] not in visited:
                visited.add(current["id"])
                current_neighbors = neighbors(current)
                if len(current_neighbors) >= min_samples:
                    queue.extend(current_neighbors)
            cluster_assignments[current["id"]] = label

    return cluster_assignments