"""
models_db.py
==============
SQLAlchemy ORM models for AgriShield.

Tables:
- Field: farm fields (PRD section 8: farmer dashboard per field)
- RiskPrediction: stored ML inference results (history for dashboard charts)
- Alert: triggered alerts (push/SMS log, PRD section 8)
"""
import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_name = Column(String, nullable=True)
    crop = Column(String, default="Rice/Paddy")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    area_hectares = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    predictions = relationship("RiskPrediction", back_populates="field", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="field", cascade="all, delete-orphan")


class RiskPrediction(Base):
    """Stored ML inference results for dashboard history/trend charts."""
    __tablename__ = "risk_predictions"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)

    rainfall = Column(Float)
    temperature = Column(Float)
    humidity = Column(Float)
    ndvi = Column(Float)
    soil_moisture = Column(Float)

    predicted_yield = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    model_name = Column(String)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    field = relationship("Field", back_populates="predictions")


class Alert(Base):
    """Triggered alerts (push/SMS), PRD section 8."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)

    severity = Column(String, nullable=False)  # medium | high
    risk_level = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    channels = Column(String)  # comma-separated: push,sms

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    acknowledged = Column(Integer, default=0)  # 0/1 boolean

    field = relationship("Field", back_populates="alerts")
