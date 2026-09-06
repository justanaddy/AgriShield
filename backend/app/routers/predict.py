"""
predict.py
===========
Core risk prediction endpoint (PRD section 6.3 inference flow):
  Input vector (rainfall, temperature, humidity, soil_moisture)
  -> model.predict() -> predicted_yield + risk_level
  (NDVI is fetched separately for display only - not a model input,
  see ml_service.py / train.py docstrings and paper Section IX-B)

If input fields are not provided in the request, the backend auto-fills
them from live sources:
  - ndvi          <- gee_service.get_current_ndvi()
  - rainfall/temperature/humidity <- weather_service.get_seasonal_climate_summary()
  - soil_moisture <- weather_service.get_current_soil_moisture() (live
    Open-Meteo reading, rescaled onto the training data's scale - see that
    function's docstring for why a rescaling is needed rather than a raw
    passthrough; override manually per-request via PredictRequest.soil_moisture)

Also runs alert_service to check if the prediction crosses the alert
threshold, storing any triggered alert in the DB.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import Alert, Field, RiskPrediction
from app.schemas import PredictRequest, PredictResponse, RiskPredictionOut
from app.services import alert_service, gee_service, ml_service, weather_service

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
async def predict_risk(req: PredictRequest, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == req.field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    # --- Auto-fill missing inputs from live sources ---
    # Uses season-to-date (Jun-Oct kharif) climate summary so input scale
    # matches the training data's seasonal definitions (PRD 5.3) - a
    # rolling 14-day window would be on a totally different scale early
    # in the season and skew the risk prediction.
    rainfall, temperature, humidity = req.rainfall, req.temperature, req.humidity
    if rainfall is None or temperature is None or humidity is None:
        climate = await weather_service.get_seasonal_climate_summary()
        rainfall = rainfall if rainfall is not None else climate["rainfall"]
        temperature = temperature if temperature is not None else climate["temperature"]
        humidity = humidity if humidity is not None else climate["humidity"]

    soil_moisture = req.soil_moisture
    if soil_moisture is None:
        soil_data = await weather_service.get_current_soil_moisture()
        soil_moisture = soil_data["soil_moisture"]

    if not ml_service.is_loaded():
        raise HTTPException(status_code=503, detail="ML model not loaded")

    result = ml_service.predict(
        rainfall=rainfall,
        temperature=temperature,
        humidity=humidity,
        soil_moisture=soil_moisture,
    )

    # NDVI is fetched for display/dashboard purposes only - not a model
    # feature (no real historical NDVI data was available for training)
    ndvi = gee_service.get_current_ndvi()["ndvi"]

    # Store prediction history
    record = RiskPrediction(
        field_id=field.id,
        rainfall=rainfall,
        temperature=temperature,
        humidity=humidity,
        ndvi=ndvi,
        soil_moisture=soil_moisture,
        predicted_yield=result["predicted_yield"],
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        model_name=result["model_name"],
    )
    db.add(record)
    db.commit()

    # --- Alert evaluation ---
    forecast = await weather_service.get_forecast(days=7)
    alert_payload = alert_service.evaluate_risk_for_alert(
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        predicted_yield=result["predicted_yield"],
        forecast=forecast,
    )

    if alert_payload:
        alert_record = Alert(
            field_id=field.id,
            severity=alert_payload["severity"],
            risk_level=alert_payload["risk_level"],
            risk_score=alert_payload["risk_score"],
            message=alert_payload["message"],
            channels=",".join(alert_payload["channels"]),
        )
        db.add(alert_record)
        db.commit()

    result["alert"] = alert_payload
    return result


def _attach_feature_contributions(record):
    """
    Attaches the model's global feature importances onto a RiskPrediction
    ORM instance as a plain attribute (not a DB column), so RiskPredictionOut
    serializes it via from_attributes. Importances are a fixed property of
    the trained model, not stored per-prediction in the DB - see
    ml_service.predict()'s equivalent computation for the live POST /predict
    response.
    """
    metadata = ml_service.get_metadata()
    importances = metadata.get("feature_importances", {}) if metadata else {}
    record.feature_contributions = {
        feat: round(val, 3) for feat, val in importances.items()
    }
    return record


@router.get("/history/{field_id}", response_model=list[RiskPredictionOut])
def prediction_history(field_id: int, limit: int = 30, db: Session = Depends(get_db)):
    records = (
        db.query(RiskPrediction)
        .filter(RiskPrediction.field_id == field_id)
        .order_by(RiskPrediction.created_at.desc())
        .limit(limit)
        .all()
    )
    records = [_attach_feature_contributions(r) for r in records]
    return list(reversed(records))


@router.get("/latest/{field_id}", response_model=RiskPredictionOut)
def latest_prediction(field_id: int, db: Session = Depends(get_db)):
    record = (
        db.query(RiskPrediction)
        .filter(RiskPrediction.field_id == field_id)
        .order_by(RiskPrediction.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No predictions yet for this field")
    return _attach_feature_contributions(record)
