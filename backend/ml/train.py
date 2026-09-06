"""
train.py
=========
Trains crop yield/risk prediction models on historical_dataset.csv.

Features (X): rainfall, temperature, humidity, soil_moisture
Target (y):   yield (continuous, tons/hectare) -> also discretized into
              Low / Medium / High risk labels for the dashboard.

NDVI is intentionally excluded: no real historical NDVI series was
available for the 1997-2014 training years (Sentinel-2 only from 2015,
Landsat NDVI for the earlier years not yet computed - see paper Section
IX-B / Limitations). Live NDVI is still fetched and displayed on the
dashboard for situational awareness, just not used as a model input.

Compares RandomForestRegressor and XGBoostRegressor via cross-validation,
saves the best model as crop_risk_model.pkl alongside metadata needed for
inference (feature names, risk thresholds, feature importances).

Run:
    python train.py
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from xgboost import XGBRegressor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "historical_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "crop_risk_model.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

FEATURES = ["rainfall", "temperature", "humidity", "soil_moisture"]
TARGET = "yield"


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def yield_to_risk(yield_value, low_thresh, high_thresh):
    """
    Discretize continuous yield prediction into risk level.
    Lower yield => higher risk.
    """
    if yield_value < low_thresh:
        return "High"
    elif yield_value < high_thresh:
        return "Medium"
    else:
        return "Low"


def main():
    print(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} rows")
    print(df.describe())

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    # --- Random Forest ---
    rf = RandomForestRegressor(
        n_estimators=200, max_depth=6, random_state=42, min_samples_leaf=2
    )
    rf_scores = cross_val_score(
        rf, X_train, y_train, cv=kf, scoring="neg_root_mean_squared_error"
    )
    rf_rmse = -rf_scores.mean()
    print(f"\nRandomForest CV RMSE: {rf_rmse:.4f} (+/- {rf_scores.std():.4f})")

    # --- XGBoost ---
    xgb = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
        reg_lambda=1.0,
    )
    xgb_scores = cross_val_score(
        xgb, X_train, y_train, cv=kf, scoring="neg_root_mean_squared_error"
    )
    xgb_rmse = -xgb_scores.mean()
    print(f"XGBoost CV RMSE: {xgb_rmse:.4f} (+/- {xgb_scores.std():.4f})")

    # --- Pick best model ---
    if rf_rmse <= xgb_rmse:
        print("\nSelected model: RandomForestRegressor")
        best_model = rf
        best_name = "RandomForestRegressor"
        best_cv_rmse = rf_rmse
    else:
        print("\nSelected model: XGBRegressor")
        best_model = xgb
        best_name = "XGBRegressor"
        best_cv_rmse = xgb_rmse

    # Fit on full training set, evaluate on held-out test set
    best_model.fit(X_train, y_train)
    y_pred_test = best_model.predict(X_test)
    test_rmse = rmse(y_test, y_pred_test)
    print(f"Test set RMSE: {test_rmse:.4f} tons/hectare")
    print(f"PRD target: RMSE < 0.3 tons/hectare -> {'PASS' if test_rmse < 0.3 else 'FAIL'}")

    # Refit on ALL data for the final deployed model
    best_model.fit(X, y)

    # Feature importances
    importances = dict(zip(FEATURES, best_model.feature_importances_.tolist()))
    print("\nFeature importances:")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"  {feat}: {imp:.3f}")

    # Risk thresholds: tertiles of historical yield distribution
    low_thresh = float(y.quantile(0.33))
    high_thresh = float(y.quantile(0.66))
    print(f"\nRisk thresholds -> High risk if yield < {low_thresh:.2f}, "
          f"Low risk if yield >= {high_thresh:.2f}, else Medium")

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(best_model, MODEL_PATH)
    print(f"\nSaved model to {MODEL_PATH}")

    # Save metadata for inference
    metadata = {
        "model_name": best_name,
        "features": FEATURES,
        "target": TARGET,
        "cv_rmse": best_cv_rmse,
        "test_rmse": test_rmse,
        "feature_importances": importances,
        "risk_thresholds": {
            "low_yield_threshold": low_thresh,
            "high_yield_threshold": high_thresh,
        },
        "training_rows": len(df),
        "field": {
            "name": "Belagavi Demo Field",
            "lat": 15.8497,
            "lon": 74.4977,
            "crop": "Rice/Paddy",
        },
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {METADATA_PATH}")


if __name__ == "__main__":
    main()
