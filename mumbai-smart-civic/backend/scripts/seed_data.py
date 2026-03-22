import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bson import ObjectId

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env", override=True)
except Exception:
    pass

from app.core.database import close_mongo_connection, connect_to_mongo, get_database, init_indexes
from app.core.security import get_authority_level, hash_password
from app.models.complaint_model import COMPLAINTS_COLLECTION
from app.models.user_model import USERS_COLLECTION


SEED_TAG = "vega-sample-v2"
ANNOUNCEMENTS_COLLECTION = "announcements"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def upsert_user(
    *,
    name: str,
    email: str,
    password: str,
    role: str,
    authority_rank: str | None = None,
) -> str:
    db = get_database()
    email_norm = email.strip().lower()
    authority_level = get_authority_level(authority_rank) if authority_rank else None
    password_hash = hash_password(password)
    now = now_utc()

    existing = await db[USERS_COLLECTION].find_one({"email": email_norm})
    if existing:
        await db[USERS_COLLECTION].update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "name": name,
                    "role": role,
                    "authority_rank": authority_rank,
                    "authority_level": authority_level,
                    "password_hash": password_hash,
                    "updated_at": now,
                }
            },
        )
        return str(existing["_id"])

    result = await db[USERS_COLLECTION].insert_one(
        {
            "name": name,
            "email": email_norm,
            "password_hash": password_hash,
            "role": role,
            "authority_rank": authority_rank,
            "authority_level": authority_level,
            "created_at": now,
            "updated_at": now,
        }
    )
    return str(result.inserted_id)


def sample_complaints(
    citizen_user_id: str,
    authority_user_id: str,
    authority_name: str,
    authority_rank: str,
) -> list[dict]:
    citizen_oid = ObjectId(citizen_user_id)
    authority_oid = ObjectId(authority_user_id)
    base = now_utc()
    sample_voter_pool = [ObjectId() for _ in range(60)]
    image_urls = [
        "https://images.unsplash.com/photo-1503596476-1c12a8ba09a9?q=80&w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1469474968028-56623f02e42e?q=80&w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1489515217757-5fd1be406fef?q=80&w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1517022812141-23620dba5c23?q=80&w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?q=80&w=1200&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?q=80&w=1200&auto=format&fit=crop",
    ]

    rows = [
        ("Garbage spill near market", "garbage", "A Ward", "Solid Waste Management", [72.8302, 18.9217], "Open", 0.82, 3),
        ("Water leakage on street", "water", "D Ward", "Water Supply Department", [72.8479, 18.9674], "In Progress", 0.88, 9),
        ("Large pothole on main road", "road", "G South Ward", "Road Maintenance", [72.8400, 19.0178], "Open", 0.75, 30),
        ("Streetlight outage", "electricity", "K East Ward", "Electrical Department", [72.8732, 19.1163], "Resolved", 0.69, 50),
        ("Drain overflow in lane", "sewage", "L Ward", "Sewerage Operations", [72.9081, 19.0732], "Open", 0.93, 20),
        ("Overflowing garbage bin", "garbage", "A Ward", "Solid Waste Management", [72.8304, 18.9218], "In Progress", 0.79, 4),
        ("Chembur road pothole near signal", "road", "M Ward", "Road Maintenance", [72.910852, 19.048728], "Open", 0.96, 1),
        ("Garbage pile near residential block", "garbage", "M Ward", "Solid Waste Management", [72.911352, 19.049128], "Open", 0.89, 2),
        ("Water leakage near pipeline crossing", "water", "M Ward", "Water Supply Department", [72.910252, 19.048128], "In Progress", 0.87, 2),
        ("Streetlight failure near bus stop", "electricity", "M Ward", "Electrical Department", [72.911052, 19.047928], "Open", 0.81, 3),
        ("Drain overflow near market lane", "sewage", "M Ward", "Sewerage Operations", [72.909952, 19.049328], "Open", 0.92, 1),
        ("Pothole cluster near flyover turn", "road", "M Ward", "Road Maintenance", [72.911102, 19.048602], "Open", 0.94, 1),
        ("Streetlight flickering near lane 4", "electricity", "M Ward", "Electrical Department", [72.910491, 19.049721], "Open", 0.78, 4),
        ("Water pipeline seepage near school", "water", "M Ward", "Water Supply Department", [72.909883, 19.048991], "In Progress", 0.85, 5),
        ("Garbage overflow outside market gate", "garbage", "M Ward", "Solid Waste Management", [72.912032, 19.048144], "Open", 0.91, 2),
        ("Drain choke in residential pocket", "sewage", "M Ward", "Sewerage Operations", [72.910631, 19.047416], "Open", 0.9, 2),
        ("Road shoulder damaged near signal", "road", "M Ward", "Road Maintenance", [72.909472, 19.049812], "Open", 0.88, 6),
        ("Water logging near bus depot", "water", "M Ward", "Water Supply Department", [72.911772, 19.050083], "Open", 0.86, 7),
        ("Uncollected waste near temple road", "garbage", "M Ward", "Solid Waste Management", [72.908942, 19.048342], "Open", 0.83, 8),
        ("Streetlight outage near junction", "electricity", "M Ward", "Electrical Department", [72.912352, 19.049604], "In Progress", 0.8, 3),
        ("Sewage backflow near society gate", "sewage", "M Ward", "Sewerage Operations", [72.909211, 19.047921], "Open", 0.93, 1),
        ("Pothole strip on service road", "road", "M Ward", "Road Maintenance", [72.910063, 19.050302], "Open", 0.89, 2),
        ("Water valve leak near clinic", "water", "M Ward", "Water Supply Department", [72.911491, 19.047633], "Open", 0.84, 4),
    ]

    data = []
    seed_votes = [12, 8, 5, 3, 10, 6, 14, 11, 9, 7, 4, 15, 13, 6, 16, 8, 10, 7, 12, 9, 5, 11, 6]
    for idx, row in enumerate(rows):
        description, category, ward, department, coordinates, status, priority, age_hours = row
        created_at = base - timedelta(hours=age_hours)
        voter_count = seed_votes[idx % len(seed_votes)]
        voters = sample_voter_pool[:voter_count]
        is_resolved = status == "Resolved"
        data.append(
            {
                "user_id": citizen_oid,
                "description": description,
                "category": category,
                "status": status,
                "ward": ward,
                "priority_score": priority,
                "duplicate_group": "dup-colaba-1" if idx in {0, 5} else ("dup-chembur-1" if idx in {6, 11, 16, 21} else None),
                "department": department,
                "predicted_department": department,
                "image_url": image_urls[idx % len(image_urls)],
                "fixed_image_url": image_urls[(idx + 2) % len(image_urls)] if is_resolved else None,
                "resolution_note": (
                    "Municipal field team completed rectification and verified closure on site."
                    if is_resolved
                    else None
                ),
                "resolved_by": (
                    {
                        "id": str(authority_oid),
                        "name": authority_name,
                        "role": "authority",
                        "authority_rank": authority_rank,
                    }
                    if is_resolved
                    else None
                ),
                "resolved_at": created_at + timedelta(hours=4) if is_resolved else None,
                "upvotes_count": voter_count,
                "upvoted_by": voters,
                "location": {"type": "Point", "coordinates": coordinates},
                "created_at": created_at,
                "updated_at": created_at,
                "seed_tag": SEED_TAG,
            }
        )
    return data


def sample_announcements() -> list[dict]:
    base = now_utc()
    return [
        {
            "title": "Municipal Operations Bulletin",
            "message": "Road resurfacing and pothole patching teams are deployed across M, L, and G South wards with priority routing for high-impact complaints.",
            "severity": "info",
            "created_at": base - timedelta(hours=1),
            "seed_tag": SEED_TAG,
        },
        {
            "title": "Monsoon Infrastructure Advisory",
            "message": "Preventive drain de-silting and storm-water line inspections are in progress. Citizens are requested to submit geo-tagged photo evidence for blocked drains.",
            "severity": "warning",
            "created_at": base - timedelta(hours=8),
            "seed_tag": SEED_TAG,
        },
        {
            "title": "Critical Public Safety Notice",
            "message": "Complaints related to exposed electrical infrastructure or major road collapse are escalated directly to emergency control teams after validation.",
            "severity": "critical",
            "created_at": base - timedelta(days=1),
            "seed_tag": SEED_TAG,
        },
    ]


async def seed() -> None:
    authority_name = os.getenv("SEED_AUTHORITY_NAME", "Vega Authority")
    authority_email = os.getenv("SEED_AUTHORITY_EMAIL", "authority@example.com")
    authority_password = os.getenv("SEED_AUTHORITY_PASSWORD", "Authority@12345")
    authority_rank = os.getenv("SEED_AUTHORITY_RANK", "commissioner")

    citizen_name = os.getenv("SEED_CITIZEN_NAME", "Vega Citizen")
    citizen_email = os.getenv("SEED_CITIZEN_EMAIL", "citizen@example.com")
    citizen_password = os.getenv("SEED_CITIZEN_PASSWORD", "Citizen@12345")

    await connect_to_mongo()
    await init_indexes()
    db = get_database()

    try:
        authority_id = await upsert_user(
            name=authority_name,
            email=authority_email,
            password=authority_password,
            role="authority",
            authority_rank=authority_rank,
        )
        citizen_id = await upsert_user(
            name=citizen_name,
            email=citizen_email,
            password=citizen_password,
            role="citizen",
        )

        await db[COMPLAINTS_COLLECTION].delete_many({"seed_tag": SEED_TAG})
        complaints = sample_complaints(
            citizen_id,
            authority_id,
            authority_name,
            authority_rank,
        )
        if complaints:
            await db[COMPLAINTS_COLLECTION].insert_many(complaints)

        await db[ANNOUNCEMENTS_COLLECTION].delete_many({"seed_tag": SEED_TAG})
        announcements = sample_announcements()
        if announcements:
            await db[ANNOUNCEMENTS_COLLECTION].insert_many(announcements)

        print("Seed completed")
        print(f"Authority login: {authority_email} / {authority_password}")
        print(f"Citizen login: {citizen_email} / {citizen_password}")
        print(f"Inserted complaints: {len(complaints)}")
        print(f"Inserted announcements: {len(announcements)}")
        print(f"Authority user id: {authority_id}")
        print(f"Citizen user id: {citizen_id}")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(seed())
