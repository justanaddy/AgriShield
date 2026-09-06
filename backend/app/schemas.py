"""
schemas.py
============
Pydantic models for API request/response validation.
"""
import datetime

from pydantic import BaseModel, Field


# --- Field ---

class FieldBase(BaseModel):
    name: str
    owner_name: str | None = None
    crop: str = "Rice/Paddy"
    latitude: float
    longitude: float
    area_hectares: float = 1.0


class FieldCreate(FieldBase):
    pass


class FieldOut(FieldBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# --- NDVI ---

class NdviCurrentOut(BaseModel):
    ndvi: float
    date: str
    source: str
    lookback_days: int | None = Field(
        default=None,
        description=(
            "How many days back the live query had to search to find a "
            "cloud-free Sentinel-2 image (30/90/180 - see gee_service's "
            "lookback cascade). None when source is demo-cached, or 30 for "
            "a normal fresh acquisition. A value >30 indicates persistent "
            "cloud cover (e.g. kharif monsoon) pushed the live reading "
            "beyond the default operational window."
        ),
    )


class NdviTimeseriesPoint(BaseModel):
    date: str
    ndvi: float
    source: str


class NdviHeatmapOut(BaseModel):
    tile_url: str | None
    field_center: dict
    available: bool


# --- Weather ---

class CurrentWeatherOut(BaseModel):
    temperature: float
    humidity: float
    rainfall_mm: float
    wind_speed_kmh: float
    weather_code: int
    time: str
    source: str


class ForecastDayOut(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    humidity_mean: float
    rainfall_mm: float
    source: str


class ClimateSummaryOut(BaseModel):
    rainfall: float
    temperature: float | None
    humidity: float | None
    period_days: int
    source: str


class SeasonalClimateSummaryOut(BaseModel):
    rainfall: float
    temperature: float | None
    humidity: float | None
    period_days: int
    period_label: str
    source: str


# --- Prediction ---

class PredictRequest(BaseModel):
    """
    Optional manual override of inputs. If a field is omitted, the backend
    fetches/derives a default value (weather from Open-Meteo, soil_moisture
    from the historical training mean). NDVI is fetched separately for
    display purposes only (not a model feature - no real historical NDVI
    data was available for training).
    """
    field_id: int
    rainfall: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    soil_moisture: float | None = None


class PredictResponse(BaseModel):
    predicted_yield: float
    risk_level: str
    risk_score: float
    feature_contributions: dict
    model_name: str
    input_features: dict
    alert: dict | None = None


class RiskPredictionOut(BaseModel):
    id: int
    rainfall: float
    temperature: float
    humidity: float
    ndvi: float
    soil_moisture: float
    predicted_yield: float
    risk_level: str
    risk_score: float
    model_name: str
    created_at: datetime.datetime
    feature_contributions: dict = Field(
        default_factory=dict,
        description=(
            "Global feature importances from the trained model (constant "
            "across predictions - see ml_service.predict()), attached here "
            "so /predict/latest and /predict/history match the live "
            "POST /predict response shape instead of omitting this field."
        ),
    )

    class Config:
        from_attributes = True


# --- Alerts ---

class AlertOut(BaseModel):
    id: int
    severity: str
    risk_level: str
    risk_score: float
    message: str
    channels: str
    created_at: datetime.datetime
    acknowledged: int

    class Config:
        from_attributes = True
