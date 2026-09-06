"""
weather_service.py
====================
Fetches real current, forecast, and historical weather data for the fixed
Belagavi field from the Open-Meteo API (https://open-meteo.com/) - free,
no API key required.

Used for:
- Current weather conditions on the farmer dashboard
- 7-day forecast for irrigation/intervention planning
- Historical rainfall/temperature for risk model inputs
"""
import datetime
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FORECAST_URL = f"{settings.WEATHER_BASE_URL}/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


async def get_current_weather():
    """
    Returns current weather conditions for the field location.

    Returns:
        dict: temperature (C), humidity (%), rainfall (mm, last hour),
              wind_speed (km/h), weather_code, time
    """
    params = {
        "latitude": settings.FIELD_CENTER_LAT,
        "longitude": settings.FIELD_CENTER_LON,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
        "timezone": "Asia/Kolkata",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(FORECAST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data["current"]
        return {
            "temperature": current["temperature_2m"],
            "humidity": current["relative_humidity_2m"],
            "rainfall_mm": current["precipitation"],
            "wind_speed_kmh": current["wind_speed_10m"],
            "weather_code": current["weather_code"],
            "time": current["time"],
            "source": "open-meteo-live",
        }
    except Exception as e:
        logger.warning(f"Open-Meteo current weather fetch failed: {e}. Using demo data.")
        return _demo_current_weather()


async def get_forecast(days=7):
    """
    Returns a `days`-day forecast for the field location, used for the
    "alert-to-action lead time >= 5 days" PRD requirement.

    Returns:
        list of dicts: [{date, temp_max, temp_min, humidity_mean, rainfall_mm}, ...]
    """
    params = {
        "latitude": settings.FIELD_CENTER_LAT,
        "longitude": settings.FIELD_CENTER_LON,
        "daily": "temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean,precipitation_sum",
        "forecast_days": days,
        "timezone": "Asia/Kolkata",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(FORECAST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily = data["daily"]
        results = []
        for i, date in enumerate(daily["time"]):
            results.append({
                "date": date,
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "humidity_mean": daily["relative_humidity_2m_mean"][i],
                "rainfall_mm": daily["precipitation_sum"][i],
                "source": "open-meteo-live",
            })
        return results
    except Exception as e:
        logger.warning(f"Open-Meteo forecast fetch failed: {e}. Using demo data.")
        return _demo_forecast(days)


async def get_recent_climate_summary(days=14):
    """
    Returns averaged recent climate data (rainfall, temperature, humidity)
    suitable as direct input features to the ML risk model.

    Returns:
        dict: rainfall (mm total over period), temperature (avg C), humidity (avg %)
    """
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)

    params = {
        "latitude": settings.FIELD_CENTER_LAT,
        "longitude": settings.FIELD_CENTER_LON,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
        "timezone": "Asia/Kolkata",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(ARCHIVE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily = data["daily"]
        temps = [t for t in daily["temperature_2m_mean"] if t is not None]
        hums = [h for h in daily["relative_humidity_2m_mean"] if h is not None]
        rains = [r for r in daily["precipitation_sum"] if r is not None]

        return {
            "rainfall": round(sum(rains), 1),
            "temperature": round(sum(temps) / len(temps), 1) if temps else None,
            "humidity": round(sum(hums) / len(hums), 1) if hums else None,
            "period_days": days,
            "source": "open-meteo-live",
        }
    except Exception as e:
        logger.warning(f"Open-Meteo archive fetch failed: {e}. Using demo data.")
        return _demo_climate_summary(days)


async def get_current_soil_moisture():
    """
    Returns a live soil-moisture estimate for the field location from
    Open-Meteo (variable: soil_moisture_0_to_7cm), rescaled onto the same
    scale as the training data's soil_moisture feature.

    IMPORTANT - these are two different physical quantities, not the same
    measurement from two sources:
      - Training data (Table I / historical_dataset.csv): NASA POWER
        GWETROOT, root-zone soil wetness expressed as a % of saturation
        (observed range ~78-91% across the 18 training years).
      - This live source: Open-Meteo's soil_moisture_0_to_7cm, shallow
        (0-7cm) volumetric water content in m3/m3 (typically ~0.05-0.45).

    Feeding the raw Open-Meteo value straight into the model would push
    live inputs far outside the training distribution and cause the same
    kind of extrapolation failure documented for the old 14-day rainfall
    window (Section XII-A of the paper). Instead we linearly rescale the
    live volumetric value onto the training feature's observed range, so
    "wetter than usual" / "drier than usual" live readings map onto a
    comparable position in the training distribution. This is a disclosed
    approximation, not a unit conversion - see README / paper limitations.

    Returns:
        dict: soil_moisture (%, rescaled onto training-data range),
              raw_value (float, original m3/m3 reading), time, source
    """
    om_min, om_max = 0.05, 0.45          # typical Open-Meteo volumetric range
    train_min, train_max = 78.0, 91.4    # observed range in historical_dataset.csv

    params = {
        "latitude": settings.FIELD_CENTER_LAT,
        "longitude": settings.FIELD_CENTER_LON,
        "hourly": "soil_moisture_0_to_7cm",
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(FORECAST_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        hourly = data["hourly"]
        times = hourly["time"]
        values = hourly["soil_moisture_0_to_7cm"]

        now = datetime.datetime.now()
        current_hour_str = now.strftime("%Y-%m-%dT%H:00")
        idx = times.index(current_hour_str) if current_hour_str in times else 0
        raw_value = values[idx]

        if raw_value is None:
            raise ValueError("soil_moisture_0_to_7cm returned null for this hour")

        clamped = max(om_min, min(om_max, raw_value))
        rescaled = train_min + (clamped - om_min) / (om_max - om_min) * (train_max - train_min)

        return {
            "soil_moisture": round(rescaled, 1),
            "raw_value": raw_value,
            "time": times[idx],
            "source": "open-meteo-live",
        }
    except Exception as e:
        logger.warning(f"Open-Meteo soil moisture fetch failed: {e}. Using demo data.")
        return _demo_soil_moisture()


async def get_seasonal_climate_summary(season_start_month=6, season_start_day=1):
    """
    Returns climate data for the most recently COMPLETED Kharif season
    (Jun 1 - Oct 31 of the previous year), matching the training data's
    definition (full-season totals/averages - PRD section 5.3).

    This is the function used for ML model inputs. A partial season-to-date
    figure (e.g. 13 days into June) would be on a completely different scale
    than the full 5-month seasonal totals the model was trained on, so we
    always use the last full season as the representative input until that
    season's normals are superseded by a fresh trained model.

    Returns:
        dict: rainfall (mm, full season total), temperature (avg C),
              humidity (avg %), period_days (int), period_label (str), source (str)
    """
    today = datetime.date.today()

    # Most recently completed season: if we're past Oct 31 this year, that's
    # this year's season; otherwise it's last year's.
    this_year_season_end = datetime.date(today.year, 10, 31)
    if today > this_year_season_end:
        season_year = today.year
    else:
        season_year = today.year - 1

    start = datetime.date(season_year, season_start_month, season_start_day)
    end = datetime.date(season_year, 10, 31)
    period_label = f"{start.isoformat()} to {end.isoformat()} (last completed kharif season)"

    params = {
        "latitude": settings.FIELD_CENTER_LAT,
        "longitude": settings.FIELD_CENTER_LON,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
        "timezone": "Asia/Kolkata",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(ARCHIVE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily = data["daily"]
        temps = [t for t in daily["temperature_2m_mean"] if t is not None]
        hums = [h for h in daily["relative_humidity_2m_mean"] if h is not None]
        rains = [r for r in daily["precipitation_sum"] if r is not None]

        period_days = (end - start).days + 1

        return {
            "rainfall": round(sum(rains), 1),
            "temperature": round(sum(temps) / len(temps), 1) if temps else None,
            "humidity": round(sum(hums) / len(hums), 1) if hums else None,
            "period_days": period_days,
            "period_label": period_label,
            "source": "open-meteo-live",
        }
    except Exception as e:
        logger.warning(f"Open-Meteo seasonal fetch failed: {e}. Using demo data.")
        return _demo_seasonal_climate_summary()


# ---------------------------------------------------------------------------
# Demo / fallback data (used if Open-Meteo is unreachable)
# Calibrated to typical Belagavi kharif-season conditions (Jun-Oct)
# ---------------------------------------------------------------------------

def _demo_current_weather():
    return {
        "temperature": 27.4,
        "humidity": 78,
        "rainfall_mm": 0.4,
        "wind_speed_kmh": 9.2,
        "weather_code": 3,
        "time": datetime.datetime.now().isoformat(),
        "source": "demo-cached",
    }


def _demo_forecast(days=7):
    today = datetime.date.today()
    results = []
    base_rain = [2.1, 0.0, 5.4, 12.8, 0.3, 0.0, 1.2]
    for i in range(days):
        date = today + datetime.timedelta(days=i)
        results.append({
            "date": date.isoformat(),
            "temp_max": 31.5 - (i % 3) * 0.4,
            "temp_min": 23.8 + (i % 2) * 0.3,
            "humidity_mean": 76 + (i % 4),
            "rainfall_mm": base_rain[i % len(base_rain)],
            "source": "demo-cached",
        })
    return results


def _demo_climate_summary(days=14):
    return {
        "rainfall": 64.5,
        "temperature": 27.8,
        "humidity": 77.5,
        "period_days": days,
        "source": "demo-cached",
    }


def _demo_soil_moisture():
    return {
        "soil_moisture": 84.2,
        "raw_value": None,
        "time": datetime.datetime.now().isoformat(),
        "source": "demo-cached",
    }


def _demo_seasonal_climate_summary():
    return {
        "rainfall": 1350.0,
        "temperature": 23.4,
        "humidity": 87.5,
        "period_days": 153,
        "period_label": "demo Jun-Oct season",
        "source": "demo-cached",
    }
