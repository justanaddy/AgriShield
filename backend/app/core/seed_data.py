"""
seed_data.py
==============
Seeds the database with the fixed Belagavi demo field (PRD-required single
field for v1 demo), so the dashboard has data immediately on first run.
"""
from sqlalchemy.orm import Session

from app.config import settings
from app.models_db import Field


def seed(db: Session):
    existing = db.query(Field).filter(Field.name == settings.FIELD_NAME).first()
    if existing:
        return existing

    field = Field(
        name=settings.FIELD_NAME,
        owner_name="Demo Farmer",
        crop="Rice/Paddy",
        latitude=settings.FIELD_CENTER_LAT,
        longitude=settings.FIELD_CENTER_LON,
        area_hectares=1.0,
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field
