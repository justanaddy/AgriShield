"""
Central configuration for AgriShield backend.
Loads values from environment variables / .env file.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives in the project root (one level above backend/), per the setup
# instructions in README.md (`cp ../.env.example ../.env` run from backend/).
# Resolved as an absolute path here so it's found regardless of which
# directory the server process is launched from (previously this was the
# relative string ".env", which only worked if uvicorn happened to be
# started from the project root - silently falling back to defaults
# otherwise, e.g. GEE_ENABLED appearing to stay False even when set true).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # App
    APP_NAME: str = "AgriShield"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./agrishield.db"

    # Google Earth Engine
    GEE_PROJECT_ID: str = "agrishield-499212"
    GEE_ENABLED: bool = False

    # Fixed field location - Belagavi district, Karnataka (Rice/Paddy)
    FIELD_NAME: str = "Belagavi Demo Field"
    FIELD_CENTER_LAT: float = 15.8497
    FIELD_CENTER_LON: float = 74.4977

    # Weather
    WEATHER_PROVIDER: str = "open-meteo"
    WEATHER_BASE_URL: str = "https://api.open-meteo.com/v1"

    # Alerts
    ALERT_RISK_THRESHOLD: float = 0.6
    SMS_PROVIDER_API_KEY: str = ""
    SMS_PROVIDER_FROM_NUMBER: str = ""

    # Paths
    MODEL_PATH: str = "models/crop_risk_model.pkl"
    HISTORICAL_DATA_PATH: str = "data/historical_dataset.csv"


settings = Settings()
