import React, { useState } from "react";
import FarmerDashboard from "./pages/FarmerDashboard.jsx";
import ExtensionOfficer from "./pages/ExtensionOfficer.jsx";

export default function App() {
  const [tab, setTab] = useState("farmer");

  return (
    <div>
      <h1>AgriShield</h1>
      <p className="muted">
        Belagavi Demo Field — Rice/Paddy — Precision Agriculture Decision
        Support
      </p>

      <div className="tabs">
        <button
          className={tab === "farmer" ? "active" : ""}
          onClick={() => setTab("farmer")}
        >
          Farmer Dashboard
        </button>
        <button
          className={tab === "officer" ? "active" : ""}
          onClick={() => setTab("officer")}
        >
          Extension Officer View
        </button>
      </div>

      {tab === "farmer" ? <FarmerDashboard /> : <ExtensionOfficer />}
    </div>
  );
}
