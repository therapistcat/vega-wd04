import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable

from bson import ObjectId
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_database
from app.models.user_model import USERS_COLLECTION, serialize_user


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

AUTHORITY_RANK_LEVELS = {
    "inspector": 1,
    "ward_officer": 2,
    "deputy_commissioner": 3,
    "commissioner": 4,
}


class AuthError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_authority_code_map() -> Dict[str, str]:
    return {
        "inspector": settings.authority_code_inspector,
        "ward_officer": settings.authority_code_ward_officer,
        "deputy_commissioner": settings.authority_code_deputy_commissioner,
        "commissioner": settings.authority_code_commissioner,
    }


def get_authority_level(rank: str | None) -> int | None:
    if not rank:
        return None
    return AUTHORITY_RANK_LEVELS.get(rank)


def validate_authority_code(rank: str, authority_code: str) -> bool:
    expected = get_authority_code_map().get(rank)
    if not expected:
        return False
    return expected.strip() == authority_code.strip()


def create_access_token(
    subject: str,
    role: str,
    authority_rank: str | None = None,
    authority_level: int | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: Dict[str, Any] = {"sub": subject, "role": role, "exp": expire_at}
    if authority_rank:
        payload["authority_rank"] = authority_rank
    if authority_level is not None:
        payload["authority_level"] = authority_level
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject: str | None = payload.get("sub")
        if subject is None:
            raise AuthError()
    except JWTError as exc:
        raise AuthError() from exc

    try:
        user_id = ObjectId(subject)
    except Exception as exc:
        raise AuthError("Invalid token subject") from exc

    user = await db[USERS_COLLECTION].find_one({"_id": user_id})
    if not user:
        raise AuthError("User no longer exists")
    
    if user.get("is_blocked"):
        reason = user.get("blocked_reason") or "No reason provided"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are blocked. Reason: {reason}"
        )

    return serialize_user(user)


def require_roles(allowed_roles: Iterable[str]):
    async def role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user["role"] not in set(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_dependency


def require_ngo():
    async def ngo_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        if current_user.get("role") != "ngo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="NGO access required",
            )
        return current_user

    return ngo_dependency


def _effective_authority_level(current_user: Dict[str, Any]) -> int:
    if current_user.get("role") == "admin":
        return AUTHORITY_RANK_LEVELS["commissioner"]

    stored_level = current_user.get("authority_level")
    if isinstance(stored_level, int):
        return stored_level

    derived = get_authority_level(current_user.get("authority_rank"))
    if derived is None:
        return 0
    return derived


def require_authority(min_level: int = 1):
    async def authority_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        if current_user.get("role") not in {"authority", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authority access required",
            )

        if _effective_authority_level(current_user) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient authority rank",
            )
        return current_user

    return authority_dependency


async def verify_vapi_token(authorization: str | None = Header(default=None)) -> bool:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing auth header")

    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    expected = settings.vapi_service_token
    if not expected:
        raise HTTPException(status_code=503, detail="Vapi service token not configured")

    if hmac.compare_digest(token, expected):
        return True

    raise HTTPException(status_code=403, detail="Invalid token")
