import React from "react";

export default function RiskCard({ prediction, onRefresh, loading }) {
  if (!prediction) {
    return (
      <div className="section">
        <h2>Risk Prediction</h2>
        <p className="muted">No prediction yet.</p>
        <button className="primary" onClick={onRefresh} disabled={loading}>
          {loading ? "Running..." : "Run Prediction"}
        </button>
      </div>
    );
  }

  const { predicted_yield, risk_level, risk_score, model_name } = prediction;
  const feature_contributions = prediction.feature_contributions || {};
  const input_features = prediction.input_features || {
    rainfall: prediction.rainfall,
    temperature: prediction.temperature,
    humidity: prediction.humidity,
    soil_moisture: prediction.soil_moisture,
  };

  return (
    <div className="section">
      <h2>Risk Prediction</h2>
      <table>
        <tbody>
          <tr>
            <th>Predicted Yield</th>
            <td>{predicted_yield} tons/hectare</td>
          </tr>
          <tr>
            <th>Risk Level</th>
            <td className={`risk-${risk_level}`}>{risk_level}</td>
          </tr>
          <tr>
            <th>Risk Score</th>
            <td>{risk_score}</td>
          </tr>
          <tr>
            <th>Model</th>
            <td>{model_name}</td>
          </tr>
        </tbody>
      </table>

      {Object.keys(input_features).length > 0 && (
        <>
          <h3>Input Features Used</h3>
          <table>
            <thead>
              <tr>
                <th>Feature</th>
                <th>Value</th>
                <th>Importance</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(input_features).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{v}</td>
                  <td>{feature_contributions[k] ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <button className="primary" onClick={onRefresh} disabled={loading}>
        {loading ? "Running..." : "Re-run Prediction"}
      </button>
    </div>
  );
}
