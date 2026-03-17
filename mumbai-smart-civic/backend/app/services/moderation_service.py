from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.user_model import USERS_COLLECTION

class ModerationService:
    @staticmethod
    async def block_user(
        db: AsyncIOMotorDatabase, 
        user_id: str, 
        authority_id: str, 
        reason: str
    ) -> bool:
        try:
            oid = ObjectId(user_id)
            auth_oid = ObjectId(authority_id)
        except Exception:
            return False

        result = await db[USERS_COLLECTION].update_one(
            {"_id": oid},
            {
                "$set": {
                    "is_blocked": True,
                    "blocked_reason": reason,
                    "blocked_at": datetime.now(timezone.utc),
                    "blocked_by": str(auth_oid),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    async def unblock_user(db: AsyncIOMotorDatabase, user_id: str) -> bool:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return False

        result = await db[USERS_COLLECTION].update_one(
            {"_id": oid},
            {
                "$set": {
                    "is_blocked": False,
                    "blocked_reason": None,
                    "blocked_at": None,
                    "blocked_by": None,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    async def get_moderation_status(db: AsyncIOMotorDatabase, user_id: str) -> dict | None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None

        user = await db[USERS_COLLECTION].find_one(
            {"_id": oid},
            {"is_blocked": 1, "blocked_reason": 1, "blocked_at": 1, "blocked_by": 1}
        )
        if not user:
            return None
            
        return {
            "is_blocked": user.get("is_blocked", False),
            "blocked_reason": user.get("blocked_reason"),
            "blocked_at": str(user["blocked_at"]) if user.get("blocked_at") else None,
            "blocked_by": user.get("blocked_by")
        }

    @staticmethod
    async def list_blocked_users(db: AsyncIOMotorDatabase) -> list[dict]:
        cursor = db[USERS_COLLECTION].find({"is_blocked": True})
        users = await cursor.to_list(length=1000)
        return [
            {
                "id": str(u["_id"]),
                "name": u.get("name"),
                "email": u.get("email"),
                "blocked_reason": u.get("blocked_reason"),
                "blocked_at": u.get("blocked_at"),
                "blocked_by": u.get("blocked_by"),
            }
            for u in users
        ]
