"""
fetch_real_historical.py
==========================
Helper script to build a REAL historical_dataset.csv for the fixed
Belagavi field (15.8497 N, 74.4977 E), replacing the synthetic data.

Two real, free, no-signup-needed sources are used here:

1. NASA POWER API (https://power.larc.nasa.gov/) -> real historical daily/
   monthly temperature, humidity, and root-zone soil moisture for any
   lat/lon, going back to 1981. No API key required.

2. Google Earth Engine (Sentinel-2 from 2015, Landsat from 1998) -> real
   historical NDVI for the field polygon. Requires `earthengine authenticate
   --project=agrishield-499212` to have been run locally.

3. You must separately obtain real `yield` and `rainfall` numbers for
   Belagavi district, rice crop, year-by-year, from:
   - data.gov.in -> "District-wise, season-wise crop production statistics"
   - Kaggle -> akshatgupta7/crop-yield-in-indian-states-dataset
   Put these into a file `backend/data/belagavi_yield_rainfall.csv` with
   columns: year,rainfall,yield  (rainfall in mm, yield in tons/hectare)

USAGE:
    python fetch_real_historical.py

This will produce `historical_dataset_real.csv` with columns matching the
schema expected by train.py:
    year,rainfall,temperature,humidity,ndvi,soil_moisture,yield

Once happy with it, rename/replace `historical_dataset.csv` with this file
and re-run `ml/train.py` - no other code changes needed.
"""
import csv
import os
import sys

LAT = 15.8497
LON = 74.4977
START_YEAR = 1998
END_YEAR = 2024

YIELD_RAINFALL_FILE = os.path.join(os.path.dirname(__file__), "belagavi_yield_rainfall.csv")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "historical_dataset_real.csv")


def fetch_nasa_power_climate(lat, lon, start_year, end_year):
    """
    Fetch real historical annual-average temperature (T2M), relative
    humidity (RH2M), and root-zone soil moisture (GWETROOT) from NASA POWER.

    Returns dict: {year: {"temperature": .., "humidity": .., "soil_moisture": ..}}
    """
    import httpx

    url = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    params = {
        "parameters": "T2M,RH2M,GWETROOT",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": str(start_year),
        "end": str(end_year),
        "format": "JSON",
    }
    print(f"Fetching NASA POWER climate data for ({lat}, {lon}), {start_year}-{end_year} ...")
    resp = httpx.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    params_data = data["properties"]["parameter"]
    t2m = params_data["T2M"]      # e.g. {"199801": 25.3, ...}
    rh2m = params_data["RH2M"]
    gwetroot = params_data["GWETROOT"]  # fraction 0-1

    result = {}
    for year in range(start_year, end_year + 1):
        # Average over Jun-Oct (kharif / paddy growing season) months
        months = [f"{year}{m:02d}" for m in range(6, 11)]
        temps = [t2m[m] for m in months if m in t2m]
        hums = [rh2m[m] for m in months if m in rh2m]
        soils = [gwetroot[m] for m in months if m in gwetroot]

        if not temps:
            continue

        result[year] = {
            "temperature": round(sum(temps) / len(temps), 2),
            "humidity": round(sum(hums) / len(hums), 2),
            # convert fraction (0-1) to percentage (0-100) for soil_moisture column
            "soil_moisture": round(sum(soils) / len(soils) * 100, 2),
        }

    return result


def fetch_gee_ndvi(lat, lon, start_year, end_year, project_id="agrishield-499212"):
    """
    Fetch real historical annual-peak NDVI for the field polygon using
    Google Earth Engine. Requires local `earthengine authenticate` to have
    been run for the given project.

    Returns dict: {year: ndvi_value}
    """
    try:
        import ee
    except ImportError:
        print("earthengine-api not installed. Run: pip install earthengine-api")
        return {}

    try:
        ee.Initialize(project=project_id)
    except Exception as e:
        print(f"GEE not authenticated/initialized: {e}")
        print("Run: earthengine authenticate --project=" + project_id)
        return {}

    # ~1km x 1km box around the field center
    delta = 0.0045
    field = ee.Geometry.Rectangle([lon - delta, lat - delta, lon + delta, lat + delta])

    result = {}
    for year in range(start_year, end_year + 1):
        # Sentinel-2 available from 2015; Landsat 5/7/8 for earlier years
        if year >= 2015:
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterDate(f"{year}-06-01", f"{year}-10-31")
                .filterBounds(field)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
            )

            def add_ndvi(img):
                return img.normalizedDifference(["B8", "B4"]).rename("NDVI")

        else:
            collection = (
                ee.ImageCollection("LANDSAT/LT05/C02/T1_L2")
                .filterDate(f"{year}-06-01", f"{year}-10-31")
                .filterBounds(field)
                .filter(ee.Filter.lt("CLOUD_COVER", 30))
            )

            def add_ndvi(img):
                # Landsat 5 SR: NIR=SR_B4, Red=SR_B3 (scaled)
                nir = img.select("SR_B4").multiply(0.0000275).add(-0.2)
                red = img.select("SR_B3").multiply(0.0000275).add(-0.2)
                return nir.subtract(red).divide(nir.add(red)).rename("NDVI")

        ndvi_collection = collection.map(add_ndvi)

        try:
            mean_ndvi = ndvi_collection.select("NDVI").mean()
            value = mean_ndvi.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=field, scale=30
            ).get("NDVI").getInfo()
            if value is not None:
                result[year] = round(value, 3)
                print(f"  {year}: NDVI={value:.3f}")
        except Exception as e:
            print(f"  {year}: failed ({e})")

    return result


def load_yield_rainfall():
    """Load real year, rainfall, yield data that you provide manually."""
    if not os.path.exists(YIELD_RAINFALL_FILE):
        print(f"\nMISSING: {YIELD_RAINFALL_FILE}")
        print("Create this file with columns: year,rainfall,yield")
        print("Source it from data.gov.in or Kaggle (see script docstring).")
        return {}

    result = {}
    with open(YIELD_RAINFALL_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            result[int(row["year"])] = {
                "rainfall": float(row["rainfall"]),
                "yield": float(row["yield"]),
            }
    return result


def main():
    climate = fetch_nasa_power_climate(LAT, LON, START_YEAR, END_YEAR)
    ndvi = fetch_gee_ndvi(LAT, LON, START_YEAR, END_YEAR)
    yield_rainfall = load_yield_rainfall()

    rows = []
    for year in range(START_YEAR, END_YEAR + 1):
        if year not in climate:
            continue
        row = {
            "year": year,
            "rainfall": yield_rainfall.get(year, {}).get("rainfall", ""),
            "temperature": climate[year]["temperature"],
            "humidity": climate[year]["humidity"],
            "ndvi": ndvi.get(year, ""),
            "soil_moisture": climate[year]["soil_moisture"],
            "yield": yield_rainfall.get(year, {}).get("yield", ""),
        }
        rows.append(row)

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["year", "rainfall", "temperature", "humidity", "ndvi", "soil_moisture", "yield"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_FILE}")
    print("Fill any blank 'rainfall'/'yield'/'ndvi' cells, then rename this")
    print("file to 'historical_dataset.csv' and re-run ml/train.py")


if __name__ == "__main__":
    sys.exit(main())
