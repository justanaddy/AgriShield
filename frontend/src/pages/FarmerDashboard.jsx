import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import Dashboard from "../components/Dashboard.jsx";

export default function FarmerDashboard() {
  const [field, setField] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getFields()
      .then((fields) => {
        if (fields.length === 0) {
          setError("No fields found. Backend seeding may not have run.");
        } else {
          setField(fields[0]);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p style={{ color: "red" }}>Error: {error}</p>;
  if (!field) return <p className="muted">Loading field...</p>;

  return (
    <div>
      <div className="section">
        <h2>{field.name}</h2>
        <p className="muted">
          Crop: {field.crop} | Location: {field.latitude}, {field.longitude} |
          Area: {field.area_hectares} ha
        </p>
      </div>
      <Dashboard field={field} />
    </div>
  );
}
