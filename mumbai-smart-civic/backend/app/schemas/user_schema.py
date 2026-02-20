from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    citizen = "citizen"
    authority = "authority"
    admin = "admin"  # legacy support


class LoginAs(str, Enum):
    citizen = "citizen"
    authority = "authority"


class AuthorityRank(str, Enum):
    inspector = "inspector"
    ward_officer = "ward_officer"
    deputy_commissioner = "deputy_commissioner"
    commissioner = "commissioner"


class CitizenRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthorityRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    authority_rank: AuthorityRank
    authority_code: str = Field(min_length=4, max_length=64)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    login_as: LoginAs
    authority_code: str | None = Field(default=None, min_length=4, max_length=64)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    authority_rank: AuthorityRank | None = None
    authority_level: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    authority_rank: AuthorityRank | None = None
    authority_level: int | None = None
