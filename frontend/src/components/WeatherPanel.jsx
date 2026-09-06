import React from "react";

export default function WeatherPanel({ current, forecast, climateSummary }) {
  return (
    <div className="section">
      <h2>Weather</h2>

      {current && (
        <table>
          <tbody>
            <tr>
              <th>Temperature</th>
              <td>{current.temperature}°C</td>
            </tr>
            <tr>
              <th>Humidity</th>
              <td>{current.humidity}%</td>
            </tr>
            <tr>
              <th>Rainfall (current)</th>
              <td>{current.rainfall_mm} mm</td>
            </tr>
            <tr>
              <th>Wind Speed</th>
              <td>{current.wind_speed_kmh} km/h</td>
            </tr>
            <tr>
              <th>Source</th>
              <td>{current.source}</td>
            </tr>
          </tbody>
        </table>
      )}

      {climateSummary && (
        <p className="muted">
          Last {climateSummary.period_days} days: {climateSummary.rainfall}mm
          rainfall, avg temp {climateSummary.temperature}°C, avg humidity{" "}
          {climateSummary.humidity}% (source: {climateSummary.source})
        </p>
      )}

      <h3>7-Day Forecast</h3>
      {forecast && forecast.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Temp Max</th>
              <th>Temp Min</th>
              <th>Humidity</th>
              <th>Rainfall</th>
            </tr>
          </thead>
          <tbody>
            {forecast.map((d) => (
              <tr key={d.date}>
                <td>{d.date}</td>
                <td>{d.temp_max}°C</td>
                <td>{d.temp_min}°C</td>
                <td>{d.humidity_mean}%</td>
                <td>{d.rainfall_mm} mm</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">No forecast data.</p>
      )}
      {forecast && forecast[0] && (
        <p className="muted">Data source: {forecast[0].source}</p>
      )}
    </div>
  );
}
