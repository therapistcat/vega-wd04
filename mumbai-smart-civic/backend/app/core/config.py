from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    project_name: str = "Mumbai Smart Civic Portal"
    api_v1_prefix: str = "/api/v1"

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "mumbai_smart_civic"

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    ml_service_url: str = "http://localhost:9000"
    ml_service_timeout_seconds: float = 2.5
    model_path: str = "app/ml_models/best.pt"
    detection_conf_threshold: float = 0.35
    detection_conf_threshold_garbage: float | None = None
    detection_conf_threshold_pothole: float | None = None
    detection_iou_threshold: float = 0.45
    detection_max_det: int = 50
    detection_autotag_threshold: float = 0.6
    detection_autotag_threshold_garbage: float | None = None
    detection_autotag_threshold_pothole: float | None = None
    detection_strict_mode: bool = False

    openai_api_key: str | None = None
    openai_api_base: str = "https://api.openai.com/v1"
    ai_agent_model: str = "gpt-4o-mini"
    ai_agent_temperature: float = 0.2
    ai_agent_timeout_seconds: float = 30.0
    ai_agent_max_tool_rounds: int = 3
    ai_agent_system_prompt: str = (
        "You are the Mumbai Smart Civic AI assistant. "
        "Start by asking the user preferred language (English, Hindi, Marathi) if not already clear. "
        "Support multilingual conversation in these languages. "
        "Use tools when user asks to create complaints, check complaint status/history, or get heatmap summary. "
        "For complaint creation, collect and confirm user name and nearest landmark first. "
        "Latitude/longitude are optional. If unavailable, proceed using landmark."
    )
    vapi_service_token: str | None = None

    duplicate_radius_meters: int = 50
    duplicate_window_hours: int = 48

    cluster_spatial_eps_meters: int = 120
    cluster_temporal_eps_hours: int = 36
    cluster_min_samples: int = 2

    authority_code_inspector: str = "MUM-INS-1101"
    authority_code_ward_officer: str = "MUM-WARD-2202"
    authority_code_deputy_commissioner: str = "MUM-DEP-3303"
    authority_code_commissioner: str = "MUM-COM-4404"

    authority_min_level_list: int = 1
    authority_min_level_status_update: int = 2
    authority_min_level_spatial_analytics: int = 3


settings = Settings()
