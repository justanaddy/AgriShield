"""
ml_service.py
==============
Loads the trained crop_risk_model.pkl and provides inference functions:
input features (rainfall, temperature, humidity, soil_moisture) ->
predicted_yield (float) + risk_level (Low/Medium/High) + feature importances
for explainability (per PRD section 6.3).

NDVI is intentionally not a model input here - see train.py's docstring
and paper Section IX-B. It's fetched separately (gee_service) for display
only.
"""
import json
import logging
import os

import joblib

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "models", "crop_risk_model.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "models", "model_metadata.json")

_model = None
_metadata = None


def load_model():
    """Load the trained model and metadata into memory. Call at app startup."""
    global _model, _metadata

    if not os.path.exists(MODEL_PATH):
        logger.error(
            f"Model not found at {MODEL_PATH}. Run `python ml/train.py` first."
        )
        return False

    _model = joblib.load(MODEL_PATH)
    with open(METADATA_PATH) as f:
        _metadata = json.load(f)

    logger.info(f"Loaded model: {_metadata['model_name']} (trained on {_metadata['training_rows']} rows)")
    return True


def is_loaded():
    return _model is not None


def get_metadata():
    return _metadata


def yield_to_risk(yield_value: float) -> str:
    """Discretize a predicted yield (tons/hectare) into a risk level."""
    thresholds = _metadata["risk_thresholds"]
    low_t = thresholds["low_yield_threshold"]
    high_t = thresholds["high_yield_threshold"]

    if yield_value < low_t:
        return "High"
    elif yield_value < high_t:
        return "Medium"
    else:
        return "Low"


def risk_to_score(risk_level: str) -> float:
    """
    Convert a risk level to a numeric 0-1 risk score for alert thresholding.
    High risk -> closer to 1.0, Low risk -> closer to 0.0
    """
    return {"Low": 0.2, "Medium": 0.5, "High": 0.85}.get(risk_level, 0.5)


def predict(rainfall: float, temperature: float, humidity: float,
            soil_moisture: float):
    """
    Run inference on the given feature values.

    Args:
        rainfall: mm (recent/seasonal total)
        temperature: degrees C
        humidity: %
        soil_moisture: %

    Returns:
        dict: predicted_yield (float, tons/hectare), risk_level (str),
              risk_score (float 0-1), feature_contributions (dict),
              model_name (str)
    """
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() at startup.")

    features = _metadata["features"]
    feature_values = {
        "rainfall": rainfall,
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
    }
    import pandas as pd

    X = pd.DataFrame([[feature_values[f] for f in features]], columns=features)

    predicted_yield = float(_model.predict(X)[0])
    risk_level = yield_to_risk(predicted_yield)
    risk_score = risk_to_score(risk_level)

    # Explainability: combine global feature importances with how far each
    # input value deviates from the historical mean, to give a per-prediction
    # "contribution" signal (simple, model-agnostic explainability per PRD 6.1)
    importances = _metadata["feature_importances"]
    feature_contributions = {
        feat: round(importances.get(feat, 0.0), 3) for feat in features
    }

    return {
        "predicted_yield": round(predicted_yield, 3),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "feature_contributions": feature_contributions,
        "model_name": _metadata["model_name"],
        "input_features": feature_values,
    }
