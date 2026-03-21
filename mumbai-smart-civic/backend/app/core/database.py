from typing import Optional

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, GEOSPHERE

from app.core.config import settings


_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    global _client, _database
    _client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=6000)
    _database = _client[settings.mongodb_db_name]
    try:
        await _client.admin.command("ping")
    except Exception:
        _client.close()
        _client = None
        _database = None
        raise


async def close_mongo_connection() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not connected",
        )
    return _database


async def init_indexes() -> None:
    if _database is None:
        return
    db = _database

    await db["users"].create_index([("email", ASCENDING)], unique=True)
    await db["complaints"].create_index([("location", GEOSPHERE)])
    await db["complaints"].create_index([("created_at", ASCENDING)])
    await db["complaints"].create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
    await db["complaints"].create_index([("department", ASCENDING)])
    await db["complaints"].create_index([("status", ASCENDING)])
    await db["complaints"].create_index([("assigned_ngo_id", ASCENDING)])
    await db["complaints"].create_index([("upvotes_count", ASCENDING), ("created_at", ASCENDING)])
    await db["announcements"].create_index([("created_at", ASCENDING)])
    await db["blockchain_ledger"].create_index("complaint_id", unique=True, sparse=True)
    await db["blockchain_ledger"].create_index("index")
    await db["ngo_requests"].create_index([("issue_id", ASCENDING)])
    await db["ngo_requests"].create_index([("ngo_id", ASCENDING)])
    await db["ngo_requests"].create_index([("issue_id", ASCENDING), ("ngo_id", ASCENDING)])
