from pydantic import BaseModel, Field

class BlockUserRequest(BaseModel):
    reason: str = Field(..., min_length=2, max_length=500)

class ModerationStatusResponse(BaseModel):
    is_blocked: bool
    blocked_reason: str | None = None
    blocked_at: str | None = None
    blocked_by: str | None = None
