from typing import Iterable

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.complaint_model import COMPLAINTS_COLLECTION


WARD_POPULATION_MAP = {
    "A Ward": 185000,
    "B Ward": 145000,
    "C Ward": 175000,
    "D Ward": 210000,
    "E Ward": 330000,
    "F North Ward": 420000,
    "F South Ward": 385000,
    "G North Ward": 510000,
    "G South Ward": 465000,
    "H East Ward": 610000,
    "H West Ward": 540000,
    "K East Ward": 790000,
    "K West Ward": 720000,
    "L Ward": 820000,
    "M East Ward": 890000,
    "M West Ward": 840000,
    "N Ward": 620000,
    "P North Ward": 760000,
    "P South Ward": 680000,
    "R Central Ward": 700000,
    "R North Ward": 640000,
    "R South Ward": 580000,
    "S Ward": 680000,
    "T Ward": 390000,
}

SEVERITY_WEIGHT_MAP = {
    "fire": 1.0,
    "emergency": 1.0,
    "electricity": 0.9,
    "road": 0.82,
    "pothole": 0.82,
    "water": 0.72,
    "sewage": 0.7,
    "drain": 0.68,
    "garbage": 0.56,
    "waste": 0.56,
}

DEFAULT_WARD_POPULATION = 300000
DEFAULT_SEVERITY = 0.5


def _normalize_ward_name(value: str | None) -> str:
    return str(value or "").strip()


def _population_for_ward(ward: str | None) -> int:
    normalized = _normalize_ward_name(ward)
    if normalized in WARD_POPULATION_MAP:
        return WARD_POPULATION_MAP[normalized]

    lowered = normalized.lower()
    for key, population in WARD_POPULATION_MAP.items():
        if key.lower() == lowered:
            return population
    return DEFAULT_WARD_POPULATION


def _severity_for_category(category: str | None) -> float:
    lowered = str(category or "").strip().lower()
    if lowered in SEVERITY_WEIGHT_MAP:
        return SEVERITY_WEIGHT_MAP[lowered]
    for key, weight in SEVERITY_WEIGHT_MAP.items():
        if key in lowered:
            return weight
    return DEFAULT_SEVERITY


def _priority_label(score: float) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    return "LOW"


def _estimate_affected_people(
    *,
    population: int,
    severity_weight: float,
    duplicate_count: int,
    engagement: int,
) -> int:
    duplicate_factor = min(0.32, 0.05 * max(duplicate_count, 1))
    engagement_factor = min(0.08, 0.01 * max(engagement, 0))
    severity_factor = 0.04 + (severity_weight * 0.08)
    reach_ratio = min(0.45, severity_factor + duplicate_factor + engagement_factor)
    return max(50, int(population * reach_ratio))


def compute_impact_metrics(
    complaint: dict,
    *,
    duplicate_count: int,
) -> dict:
    severity_weight = _severity_for_category(complaint.get("category"))
    population = _population_for_ward(complaint.get("ward"))
    engagement = int(complaint.get("upvotes_count") or 0)

    duplicate_norm = min(1.0, max(duplicate_count, 1) / 10.0)
    population_norm = min(1.0, population / 900000.0)
    severity_norm = min(1.0, severity_weight)
    engagement_norm = min(1.0, engagement / 25.0)

    raw_score = (
        (duplicate_norm * 30.0)
        + (population_norm * 25.0)
        + (severity_norm * 30.0)
        + (engagement_norm * 15.0)
    )
    impact_score = round(min(100.0, max(0.0, raw_score)), 1)
    affected_people = _estimate_affected_people(
        population=population,
        severity_weight=severity_weight,
        duplicate_count=duplicate_count,
        engagement=engagement,
    )
    priority = _priority_label(impact_score)
    recommendation_text = (
        f"Fixing this issue first will impact approximately {affected_people:,} people in this area."
    )
    impact_reason = (
        f"Severity {int(severity_weight * 100)}%, duplicates {duplicate_count}, "
        f"ward population {population:,}, engagement {engagement}."
    )

    return {
        "duplicate_count": duplicate_count,
        "impact_score": impact_score,
        "affected_people": affected_people,
        "impact_priority": priority,
        "recommendation_text": recommendation_text,
        "impact_reason": impact_reason,
    }


async def build_duplicate_count_map(
    db: AsyncIOMotorDatabase,
    complaints: Iterable[dict],
) -> dict[str, int]:
    complaints = list(complaints)
    duplicate_groups = {
        str(item.get("duplicate_group")).strip()
        for item in complaints
        if item.get("duplicate_group")
    }
    cluster_ids = {
        str(item.get("cluster_id")).strip()
        for item in complaints
        if item.get("cluster_id")
    }

    group_counts: dict[str, int] = {}
    if duplicate_groups:
        grouped = await db[COMPLAINTS_COLLECTION].aggregate(
            [
                {"$match": {"duplicate_group": {"$in": list(duplicate_groups)}}},
                {"$group": {"_id": "$duplicate_group", "count": {"$sum": 1}}},
            ]
        ).to_list(length=len(duplicate_groups))
        group_counts = {str(row["_id"]): int(row["count"]) for row in grouped if row.get("_id")}

    cluster_counts: dict[str, int] = {}
    if cluster_ids:
        grouped = await db[COMPLAINTS_COLLECTION].aggregate(
            [
                {"$match": {"cluster_id": {"$in": list(cluster_ids)}}},
                {"$group": {"_id": "$cluster_id", "count": {"$sum": 1}}},
            ]
        ).to_list(length=len(cluster_ids))
        cluster_counts = {str(row["_id"]): int(row["count"]) for row in grouped if row.get("_id")}

    complaint_counts: dict[str, int] = {}
    for complaint in complaints:
        count = 1
        duplicate_group = complaint.get("duplicate_group")
        cluster_id = complaint.get("cluster_id")
        if duplicate_group:
            count = max(count, int(group_counts.get(str(duplicate_group), 1)))
        if cluster_id:
            count = max(count, int(cluster_counts.get(str(cluster_id), 1)))
        complaint_counts[str(complaint["_id"])] = count
    return complaint_counts


async def enrich_complaints_with_impact(
    db: AsyncIOMotorDatabase,
    complaints: Iterable[dict],
) -> list[dict]:
    complaints = list(complaints)
    duplicate_count_map = await build_duplicate_count_map(db, complaints)
    enriched: list[dict] = []
    for complaint in complaints:
        duplicate_count = duplicate_count_map.get(str(complaint["_id"]), 1)
        enriched.append(
            {
                **complaint,
                **compute_impact_metrics(complaint, duplicate_count=duplicate_count),
            }
        )
    return enriched
