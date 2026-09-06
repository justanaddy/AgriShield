"""
evaluate.py
============
Loads the trained crop_risk_model.pkl and runs evaluation against the
historical dataset, printing RMSE, per-row predictions, and risk
classification accuracy against PRD targets.

Run:
    python evaluate.py
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "historical_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "crop_risk_model.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "models", "model_metadata.json")


def yield_to_risk(yield_value, low_thresh, high_thresh):
    """
    Discretize continuous yield into a risk tier. Must match train.py and
    app/services/ml_service.py exactly - this function previously had the
    Low/Medium branches swapped relative to those two (and relative to the
    paper's own Equation 1), which mislabeled 12 of 18 years in the printed
    per-year table below even though it didn't change the RMSE or the
    aggregate risk-agreement percentage (that figure is a match/mismatch
    count between two columns both run through the same function, so a
    consistent swap doesn't change it - only the individual labels were
    wrong).
    """
    if yield_value < low_thresh:
        return "High"
    elif yield_value < high_thresh:
        return "Medium"
    else:
        return "Low"


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found at {MODEL_PATH}. Run train.py first.")
        return

    model = joblib.load(MODEL_PATH)
    with open(METADATA_PATH) as f:
        metadata = json.load(f)

    df = pd.read_csv(DATA_PATH)
    features = metadata["features"]
    X = df[features]
    y_true = df["yield"]

    y_pred = model.predict(X)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

    low_t = metadata["risk_thresholds"]["low_yield_threshold"]
    high_t = metadata["risk_thresholds"]["high_yield_threshold"]

    df_result = df.copy()
    df_result["predicted_yield"] = np.round(y_pred, 3)
    df_result["actual_risk"] = df_result["yield"].apply(
        lambda v: yield_to_risk(v, low_t, high_t)
    )
    df_result["predicted_risk"] = df_result["predicted_yield"].apply(
        lambda v: yield_to_risk(v, low_t, high_t)
    )
    risk_match = (df_result["actual_risk"] == df_result["predicted_risk"]).mean()

    print(f"Model: {metadata['model_name']}")
    print(f"Rows evaluated: {len(df)}")
    print(f"Overall RMSE: {rmse:.4f} tons/hectare (PRD target < 0.3)")
    print(f"Risk classification agreement: {risk_match * 100:.1f}%")
    print()
    print(df_result[["year", "yield", "predicted_yield", "actual_risk", "predicted_risk"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
