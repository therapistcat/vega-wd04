from __future__ import annotations

from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
from typing import Any
from uuid import uuid4


EARTH_RADIUS_METERS = 6371000.0


def _to_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(max(1e-12, 1 - a)))
    return EARTH_RADIUS_METERS * c


def _is_neighbor(
    a: dict[str, Any],
    b: dict[str, Any],
    spatial_eps_meters: float,
    temporal_eps_hours: float,
) -> bool:
    a_coords = (a.get("location") or {}).get("coordinates") or [None, None]
    b_coords = (b.get("location") or {}).get("coordinates") or [None, None]
    if None in a_coords or None in b_coords:
        return False

    a_lng, a_lat = float(a_coords[0]), float(a_coords[1])
    b_lng, b_lat = float(b_coords[0]), float(b_coords[1])
    dist = _haversine_m(a_lat, a_lng, b_lat, b_lng)
    if dist > spatial_eps_meters:
        return False

    a_dt = _to_dt(a.get("created_at"))
    b_dt = _to_dt(b.get("created_at"))
    time_gap_h = abs((a_dt - b_dt).total_seconds()) / 3600.0
    return time_gap_h <= temporal_eps_hours


def st_dbscan_cluster(
    docs: list[dict[str, Any]],
    spatial_eps_meters: int,
    temporal_eps_hours: int,
    min_samples: int,
) -> dict[str, str]:
    """
    Lightweight ST-DBSCAN style clustering.
    Returns mapping complaint_id -> duplicate_group_id for points
    that belong to clusters of size >= min_samples.
    """
    if not docs or min_samples <= 1:
        return {}

    n = len(docs)
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if _is_neighbor(
                docs[i],
                docs[j],
                spatial_eps_meters=float(spatial_eps_meters),
                temporal_eps_hours=float(temporal_eps_hours),
            ):
                adjacency[i].append(j)
                adjacency[j].append(i)

    visited = [False] * n
    assignments: dict[str, str] = {}
    for i in range(n):
        if visited[i]:
            continue
        stack = [i]
        component: list[int] = []
        visited[i] = True

        while stack:
            node = stack.pop()
            component.append(node)
            for nxt in adjacency[node]:
                if not visited[nxt]:
                    visited[nxt] = True
                    stack.append(nxt)

        if len(component) < min_samples:
            continue

        group_id = f"cluster-{uuid4().hex[:12]}"
        for idx in component:
            complaint_id = str(docs[idx].get("_id"))
            if complaint_id:
                assignments[complaint_id] = group_id

    return assignments

