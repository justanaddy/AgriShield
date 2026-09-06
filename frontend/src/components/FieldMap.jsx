import React, { useEffect, useRef } from "react";

/**
 * FieldMap
 * =========
 * Renders the field location on a Leaflet map. If a live GEE NDVI tile
 * URL is available (heatmap.available === true), overlays it as the NDVI
 * heatmap layer. Otherwise shows a plain marker with a note that the
 * heatmap requires GEE_ENABLED=true + earthengine authentication.
 *
 * Leaflet is loaded from CDN (cdnjs) - no npm dependency needed.
 */
export default function FieldMap({ heatmap, fields }) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!window.L) {
      // Load Leaflet CSS + JS from CDN if not already present
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href =
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css";
      document.head.appendChild(link);

      const script = document.createElement("script");
      script.src =
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js";
      script.onload = () => initMap();
      document.body.appendChild(script);
    } else {
      initMap();
    }

    function initMap() {
      if (mapRef.current || !containerRef.current) return;
      const center = heatmap?.field_center || { lat: 15.8497, lon: 74.4977 };

      const map = window.L.map(containerRef.current).setView(
        [center.lat, center.lon],
        14
      );

      window.L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        { attribution: "© OpenStreetMap contributors" }
      ).addTo(map);

      if (heatmap?.available && heatmap.tile_url) {
        window.L.tileLayer(heatmap.tile_url, {
          attribution: "NDVI (Sentinel-2 via Google Earth Engine)",
          opacity: 0.6,
        }).addTo(map);
      }

      (fields || []).forEach((f) => {
        window.L.marker([f.latitude, f.longitude])
          .addTo(map)
          .bindPopup(`${f.name} (${f.crop})`);
      });

      mapRef.current = map;
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [heatmap, fields]);

  return (
    <div className="section">
      <h2>Field Map {heatmap?.available ? "+ NDVI Heatmap" : ""}</h2>
      {!heatmap?.available && (
        <p className="muted">
          NDVI heatmap overlay requires GEE_ENABLED=true and Earth Engine
          authentication. Showing plain map for now.
        </p>
      )}
      <div
        ref={containerRef}
        style={{ height: "320px", width: "100%", border: "1px solid #ccc" }}
      />
    </div>
  );
}
