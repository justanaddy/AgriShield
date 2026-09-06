import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import AlertBanner from "./AlertBanner.jsx";
import FieldMap from "./FieldMap.jsx";
import NdviChart from "./NdviChart.jsx";
import RiskCard from "./RiskCard.jsx";
import WeatherPanel from "./WeatherPanel.jsx";

export default function Dashboard({ field }) {
  const [ndviCurrent, setNdviCurrent] = useState(null);
  const [ndviSeries, setNdviSeries] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [weatherCurrent, setWeatherCurrent] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [climateSummary, setClimateSummary] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState(null);

  async function loadAll() {
    try {
      const [
        ndviCur,
        ndviTs,
        hm,
        wCur,
        wForecast,
        climate,
        alertList,
      ] = await Promise.all([
        api.getNdviCurrent(),
        api.getNdviTimeseries(12),
        api.getNdviHeatmap(),
        api.getWeatherCurrent(),
        api.getWeatherForecast(7),
        api.getClimateSummary(14),
        api.getAlerts(field.id),
      ]);

      setNdviCurrent(ndviCur);
      setNdviSeries(ndviTs);
      setHeatmap(hm);
      setWeatherCurrent(wCur);
      setForecast(wForecast);
      setClimateSummary(climate);
      setAlerts(alertList);

      api
        .getLatestPrediction(field.id)
        .then(setPrediction)
        .catch(() => setPrediction(null));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [field.id]);

  async function runPrediction() {
    setPredicting(true);
    setError(null);
    try {
      const result = await api.predict(field.id);
      setPrediction(result);
      const alertList = await api.getAlerts(field.id);
      setAlerts(alertList);
    } catch (e) {
      setError(e.message);
    } finally {
      setPredicting(false);
    }
  }

  async function acknowledge(alertId) {
    await api.acknowledgeAlert(alertId);
    const alertList = await api.getAlerts(field.id);
    setAlerts(alertList);
  }

  if (error) {
    return (
      <div className="section">
        <p style={{ color: "red" }}>Error: {error}</p>
        <button onClick={loadAll}>Retry</button>
      </div>
    );
  }

  return (
    <div>
      <AlertBanner alerts={alerts} onAcknowledge={acknowledge} />

      <RiskCard prediction={prediction} onRefresh={runPrediction} loading={predicting} />

      <div className="row">
        <div className="col">
          <NdviChart current={ndviCurrent} timeseries={ndviSeries} />
        </div>
        <div className="col">
          <WeatherPanel
            current={weatherCurrent}
            forecast={forecast}
            climateSummary={climateSummary}
          />
        </div>
      </div>

      <FieldMap heatmap={heatmap} fields={[field]} />
    </div>
  );
}
