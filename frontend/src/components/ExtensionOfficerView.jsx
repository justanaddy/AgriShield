import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import FieldMap from "./FieldMap.jsx";

/**
 * ExtensionOfficerView
 * =====================
 * Multi-farm overview (PRD section 8): lists all fields with their latest
 * risk prediction, and shows them on a single map. In this v1 demo there
 * is one seeded field, but the table/map scale to multiple fields as more
 * are added via POST /fields.
 */
export default function ExtensionOfficerView() {
  const [fields, setFields] = useState([]);
  const [predictions, setPredictions] = useState({});
  const [heatmap, setHeatmap] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const fieldList = await api.getFields();
        setFields(fieldList);

        const hm = await api.getNdviHeatmap();
        setHeatmap(hm);

        const preds = {};
        await Promise.all(
          fieldList.map(async (f) => {
            try {
              preds[f.id] = await api.getLatestPrediction(f.id);
            } catch {
              preds[f.id] = null;
            }
          })
        );
        setPredictions(preds);
      } catch (e) {
        setError(e.message);
      }
    }
    load();
  }, []);

  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;

  return (
    <div>
      <div className="section">
        <h2>Field Overview</h2>
        <table>
          <thead>
            <tr>
              <th>Field</th>
              <th>Owner</th>
              <th>Crop</th>
              <th>Area (ha)</th>
              <th>Latest Predicted Yield</th>
              <th>Risk Level</th>
              <th>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((f) => {
              const p = predictions[f.id];
              return (
                <tr key={f.id}>
                  <td>{f.name}</td>
                  <td>{f.owner_name || "-"}</td>
                  <td>{f.crop}</td>
                  <td>{f.area_hectares}</td>
                  <td>{p ? `${p.predicted_yield} t/ha` : "—"}</td>
                  <td className={p ? `risk-${p.risk_level}` : ""}>
                    {p ? p.risk_level : "No prediction yet"}
                  </td>
                  <td>{p ? new Date(p.created_at).toLocaleString() : "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="muted">
          Run a prediction from the Farmer Dashboard tab to populate risk
          data for a field.
        </p>
      </div>

      <FieldMap heatmap={heatmap} fields={fields} />
    </div>
  );
}
