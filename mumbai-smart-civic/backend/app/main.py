from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import admin, auth, blockchain, citizen, detection, vapi, ngo_requests
from app.emergency.router import router as emergency_router
from app.ai.ai_agent import router as ai_agent_router
from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo, init_indexes
from app.services.detection_service import get_detection_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_connected = False
    app.state.db_error = None
    try:
        await connect_to_mongo()
        await init_indexes()
        app.state.db_connected = True
    except Exception as exc:
        app.state.db_connected = False
        app.state.db_error = str(exc)
    # Load detection model once at startup (non-fatal if missing).
    get_detection_service().load_model()
    yield
    await close_mongo_connection()


app = FastAPI(title=settings.project_name, lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.(ngrok-free\.app|ngrok\.app|ngrok\.io)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "database_connected": bool(getattr(app.state, "db_connected", False)),
        "database_error": getattr(app.state, "db_error", None),
    }


app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(citizen.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(blockchain.router, prefix=settings.api_v1_prefix)
app.include_router(detection.router, prefix=settings.api_v1_prefix)
app.include_router(ai_agent_router, prefix=settings.api_v1_prefix)
app.include_router(vapi.router, prefix=settings.api_v1_prefix)
app.include_router(ngo_requests.router, prefix=settings.api_v1_prefix)
app.include_router(emergency_router)
