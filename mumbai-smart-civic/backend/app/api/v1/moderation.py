from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.core.security import require_authority, get_current_user
from app.services.moderation_service import ModerationService
from app.schemas.moderation_schema import BlockUserRequest, ModerationStatusResponse

router = APIRouter(prefix="/moderation", tags=["moderation"])

@router.post("/block/{user_id}", status_code=status.HTTP_200_OK)
async def block_user(
    user_id: str,
    payload: BlockUserRequest,
    current_user: dict = Depends(require_authority(min_level=1)),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if user_id == str(current_user["id"]):
        raise HTTPException(status_code=400, detail="You cannot block yourself")
        
    success = await ModerationService.block_user(
        db, user_id, current_user["id"], payload.reason
    )
    if not success:
        raise HTTPException(status_code=404, detail="User not found or already blocked")
    return {"message": "User blocked successfully"}

@router.post("/unblock/{user_id}", status_code=status.HTTP_200_OK)
async def unblock_user(
    user_id: str,
    current_user: dict = Depends(require_authority(min_level=1)),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    success = await ModerationService.unblock_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or not blocked")
    return {"message": "User unblocked successfully"}

@router.get("/status/{user_id}", response_model=ModerationStatusResponse)
async def get_moderation_status(
    user_id: str,
    current_user: dict = Depends(require_authority(min_level=1)),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    status_data = await ModerationService.get_moderation_status(db, user_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="User not found")
    return status_data

@router.get("/blocked", response_model=list[dict])
async def list_blocked_users(
    current_user: dict = Depends(require_authority(min_level=1)),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    return await ModerationService.list_blocked_users(db)
