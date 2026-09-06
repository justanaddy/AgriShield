import React from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function NdviChart({ current, timeseries }) {
  return (
    <div className="section">
      <h2>NDVI (Vegetation Health)</h2>
      {current && (
        <p>
          Current NDVI: <strong>{current.ndvi}</strong> (as of {current.date},
          source: {current.source}
          {current.lookback_days && current.lookback_days > 30
            ? ` — no cloud-free image in the default 30-day window; widened to ${current.lookback_days} days`
            : ""}
          )
        </p>
      )}

      {timeseries && timeseries.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={timeseries}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="ndvi" stroke="#2e7d32" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="muted">No NDVI history available.</p>
      )}
      {timeseries && timeseries[0] && (
        <p className="muted">Data source: {timeseries[0].source}</p>
      )}
    </div>
  );
}
