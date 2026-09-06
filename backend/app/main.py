"""
main.py
========
AgriShield FastAPI application entrypoint.

On startup:
- Initializes the database (creates tables)
- Seeds the fixed Belagavi demo field
- Initializes Google Earth Engine (if GEE_ENABLED=true)
- Loads the trained ML model

Routers:
- /fields    - field CRUD
- /ndvi      - satellite NDVI (real GEE / demo fallback)
- /weather   - real Open-Meteo weather
- /predict   - ML risk inference + alerts
- /alerts    - alert listing/acknowledgement
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.seed_data import seed
from app.database import SessionLocal, init_db
from app.routers import alerts, fields, ndvi, predict, weather
from app.services import gee_service, ml_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Precision Agriculture Decision Support System - Belagavi demo field",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fields.router)
app.include_router(ndvi.router)
app.include_router(weather.router)
app.include_router(predict.router)
app.include_router(alerts.router)

_seeded_field = None


@app.on_event("startup")
async def startup_event():
    global _seeded_field

    logger.info(f"Starting {settings.APP_NAME}...")

    init_db()

    db = SessionLocal()
    try:
        _seeded_field = seed(db)
        logger.info(f"Seeded field: {_seeded_field.name} (id={_seeded_field.id})")
    finally:
        db.close()

    gee_service.init_gee()

    if not ml_service.load_model():
        logger.warning(
            "ML model not found. Run `python ml/train.py` from backend/ to generate it, "
            "then restart the server."
        )


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "field": {
            "name": settings.FIELD_NAME,
            "lat": settings.FIELD_CENTER_LAT,
            "lon": settings.FIELD_CENTER_LON,
            "crop": "Rice/Paddy",
        },
        "gee_enabled": settings.GEE_ENABLED,
        "model_loaded": ml_service.is_loaded(),
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": ml_service.is_loaded(),
    }
