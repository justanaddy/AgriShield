const BASE = "/api";

async function handle(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  getFields: () => fetch(`${BASE}/fields`).then(handle),
  getField: (id) => fetch(`${BASE}/fields/${id}`).then(handle),

  getNdviCurrent: () => fetch(`${BASE}/ndvi/current`).then(handle),
  getNdviTimeseries: (weeks = 12) =>
    fetch(`${BASE}/ndvi/timeseries?weeks=${weeks}`).then(handle),
  getNdviHeatmap: () => fetch(`${BASE}/ndvi/heatmap`).then(handle),

  getWeatherCurrent: () => fetch(`${BASE}/weather/current`).then(handle),
  getWeatherForecast: (days = 7) =>
    fetch(`${BASE}/weather/forecast?days=${days}`).then(handle),
  getClimateSummary: (days = 14) =>
    fetch(`${BASE}/weather/climate-summary?days=${days}`).then(handle),

  predict: (fieldId) =>
    fetch(`${BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field_id: fieldId }),
    }).then(handle),
  getPredictionHistory: (fieldId, limit = 30) =>
    fetch(`${BASE}/predict/history/${fieldId}?limit=${limit}`).then(handle),
  getLatestPrediction: (fieldId) =>
    fetch(`${BASE}/predict/latest/${fieldId}`).then(handle),

  getAlerts: (fieldId, unacknowledgedOnly = false) =>
    fetch(
      `${BASE}/alerts/${fieldId}?unacknowledged_only=${unacknowledgedOnly}`
    ).then(handle),
  acknowledgeAlert: (alertId) =>
    fetch(`${BASE}/alerts/${alertId}/acknowledge`, { method: "POST" }).then(
      handle
    ),
};
