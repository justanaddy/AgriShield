import React from "react";

export default function AlertBanner({ alerts, onAcknowledge }) {
  if (!alerts || alerts.length === 0) return null;

  const unacknowledged = alerts.filter((a) => !a.acknowledged);
  if (unacknowledged.length === 0) return null;

  return (
    <div className="section">
      <h2>Alerts</h2>
      {unacknowledged.map((a) => (
        <div className="alert-box" key={a.id}>
          <strong>[{a.severity.toUpperCase()}]</strong> {a.message}
          <div className="muted">
            {new Date(a.created_at).toLocaleString()} — channels:{" "}
            {a.channels}
          </div>
          <button onClick={() => onAcknowledge(a.id)}>Acknowledge</button>
        </div>
      ))}
    </div>
  );
}
