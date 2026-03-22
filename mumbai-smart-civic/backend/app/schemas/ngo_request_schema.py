from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

NGORequestStatus = Literal["pending", "approved", "rejected"]

class NGORequestCreate(BaseModel):
    issue_id: str
    issue_title: str | None = None

class NGORequestUpdate(BaseModel):
    status: NGORequestStatus

class NGORequestResponse(BaseModel):
    id: str
    issue_id: str
    issue_title: str
    ngo_id: str
    ngo_name: str
    status: NGORequestStatus
    assigned_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
