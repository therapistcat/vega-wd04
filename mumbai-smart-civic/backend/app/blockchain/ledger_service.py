from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.blockchain.chain_service import add_block


async def _safe_log_event(db: AsyncIOMotorDatabase, payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return await add_block(db, payload)
    except Exception as exc:
        print(f"[audit-ledger] failed to append block: {exc}")
        return None


def _actor_payload(actor: dict[str, Any] | None, fallback_role: str) -> dict[str, Any]:
    actor = actor or {}
    return {
        "id": str(actor.get("id") or actor.get("_id") or ""),
        "name": str(actor.get("name") or actor.get("reported_by_name") or fallback_role.title()),
        "role": str(actor.get("role") or fallback_role),
    }


async def log_complaint_created(
    db: AsyncIOMotorDatabase,
    *,
    issue: dict[str, Any],
    actor: dict[str, Any],
) -> dict[str, Any] | None:
    return await _safe_log_event(
        db,
        {
            "action_type": "COMPLAINT_CREATED",
            "issue_id": str(issue.get("id") or issue.get("_id") or ""),
            "performed_by": _actor_payload(actor, "citizen"),
            "timestamp": issue.get("created_at"),
            "metadata": {
                "description": issue.get("description"),
                "category": issue.get("category"),
                "ward": issue.get("ward"),
                "status": issue.get("status"),
            },
        },
    )


async def log_ngo_assigned(
    db: AsyncIOMotorDatabase,
    *,
    issue: dict[str, Any],
    actor: dict[str, Any],
    ngo_name: str | None,
) -> dict[str, Any] | None:
    return await _safe_log_event(
        db,
        {
            "action_type": "NGO_ASSIGNED",
            "issue_id": str(issue.get("id") or issue.get("_id") or ""),
            "performed_by": _actor_payload(actor, "admin"),
            "timestamp": issue.get("updated_at"),
            "metadata": {
                "status": issue.get("status"),
                "assigned_ngo_name": ngo_name or issue.get("assigned_ngo_name"),
                "progress_status": issue.get("progress_status"),
            },
        },
    )


async def log_issue_updated(
    db: AsyncIOMotorDatabase,
    *,
    issue: dict[str, Any],
    actor: dict[str, Any],
    message: str | None = None,
) -> dict[str, Any] | None:
    return await _safe_log_event(
        db,
        {
            "action_type": "ISSUE_UPDATED",
            "issue_id": str(issue.get("id") or issue.get("_id") or ""),
            "performed_by": _actor_payload(actor, actor.get("role") if actor else "ngo"),
            "timestamp": issue.get("updated_at"),
            "metadata": {
                "status": issue.get("status"),
                "progress_status": issue.get("progress_status"),
                "assigned_ngo_name": issue.get("assigned_ngo_name"),
                "message": message,
            },
        },
    )


async def log_issue_resolved(
    db: AsyncIOMotorDatabase,
    *,
    issue: dict[str, Any],
    actor: dict[str, Any],
    message: str | None = None,
) -> dict[str, Any] | None:
    return await _safe_log_event(
        db,
        {
            "action_type": "ISSUE_RESOLVED",
            "issue_id": str(issue.get("id") or issue.get("_id") or ""),
            "performed_by": _actor_payload(actor, actor.get("role") if actor else "admin"),
            "timestamp": issue.get("resolved_at") or issue.get("updated_at"),
            "metadata": {
                "status": issue.get("status"),
                "progress_status": issue.get("progress_status"),
                "assigned_ngo_name": issue.get("assigned_ngo_name"),
                "resolution_note": issue.get("resolution_note"),
                "message": message,
            },
        },
    )
