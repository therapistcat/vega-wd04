from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import (
    create_access_token,
    get_authority_level,
    get_current_user,
    hash_password,
    validate_authority_code,
    verify_password,
)
from app.models.user_model import USERS_COLLECTION, build_user_document, serialize_user
from app.schemas.user_schema import (
    AuthorityRegisterRequest,
    CitizenRegisterRequest,
    LoginAs,
    TokenResponse,
    UserLoginRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_citizen(
    payload: CitizenRegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> UserResponse:
    existing = await db[USERS_COLLECTION].find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")

    document = build_user_document(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="citizen",
    )
    result = await db[USERS_COLLECTION].insert_one(document)
    user = await db[USERS_COLLECTION].find_one({"_id": result.inserted_id})
    return UserResponse.model_validate(serialize_user(user))


@router.post("/register/authority", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_authority(
    payload: AuthorityRegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> UserResponse:
    existing = await db[USERS_COLLECTION].find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")

    rank = payload.authority_rank.value
    if not validate_authority_code(rank, payload.authority_code):
        raise HTTPException(status_code=403, detail="Invalid authority code for selected rank")

    authority_level = get_authority_level(rank)
    if authority_level is None:
        raise HTTPException(status_code=400, detail="Unsupported authority rank")

    document = build_user_document(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="authority",
        authority_rank=rank,
        authority_level=authority_level,
    )
    result = await db[USERS_COLLECTION].insert_one(document)
    user = await db[USERS_COLLECTION].find_one({"_id": result.inserted_id})
    return UserResponse.model_validate(serialize_user(user))


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: UserLoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> TokenResponse:
    user = await db[USERS_COLLECTION].find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    role = user.get("role")
    authority_rank = user.get("authority_rank")
    authority_level = user.get("authority_level")

    if payload.login_as == LoginAs.citizen:
        if role != "citizen":
            raise HTTPException(status_code=403, detail="This account is not a citizen account")
        authority_rank = None
        authority_level = None

    if payload.login_as == LoginAs.authority:
        if role not in {"authority", "admin"}:
            raise HTTPException(status_code=403, detail="This account is not an authority account")

        if role == "admin" and not authority_rank:
            authority_rank = "commissioner"
        if authority_level is None:
            authority_level = get_authority_level(authority_rank)

        if not payload.authority_code:
            raise HTTPException(status_code=400, detail="authority_code is required for authority login")
        if not authority_rank or not validate_authority_code(authority_rank, payload.authority_code):
            raise HTTPException(status_code=403, detail="Invalid authority code")

    if payload.login_as == LoginAs.ngo:
        if role != "ngo":
            raise HTTPException(status_code=403, detail="This account is not an NGO account")

    token = create_access_token(
        subject=str(user["_id"]),
        role=role,
        authority_rank=authority_rank,
        authority_level=authority_level,
    )
    return TokenResponse(
        access_token=token,
        role=role,
        authority_rank=authority_rank,
        authority_level=authority_level,
    )


@router.post("/mock-ngo-login", response_model=TokenResponse)
async def mock_ngo_login(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> TokenResponse:
    # Ensure a default NGO user exists or just use a placeholder OID
    # For hackathon/demo, we'll try to find an NGO or use a hardcoded OID if we don't want to seed
    user = await db[USERS_COLLECTION].find_one({"role": "ngo"})
    if not user:
        # Create a default NGO user if none exists
        document = build_user_document(
            name="NGO Sahayata",
            email="contact@ngosahayata.org",
            password_hash=hash_password("password123"), # Not used here but for consistency
            role="ngo",
        )
        result = await db[USERS_COLLECTION].insert_one(document)
        user = await db[USERS_COLLECTION].find_one({"_id": result.inserted_id})

    token = create_access_token(
        subject=str(user["_id"]),
        role="ngo",
    )
    return TokenResponse(
        access_token=token,
        role="ngo",
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
