"""
build_real_dataset.py
=======================
Merges REAL data sources into historical_dataset.csv, replacing the
synthetic generator:

1. crop_yield_district.csv (Kaggle "Indian crop production yield dataset")
   -> real Belagavi/Belgaum, Kharif season, Rice: Area, Production, yield (t/ha)
   Years available: 1997-2019

2. nasa_power_belagavi.csv (NASA POWER, exact coords 15.8497N 74.4977E)
   -> real monthly PRECTOTCORR_SUM (rainfall), T2M (temp), RH2M (humidity),
      GWETROOT (root-zone soil wetness fraction)
   Years available: 2010-2024
   Kharif season = Jun-Oct, averaged/summed over those months.

Overlap (real data for ALL fields): 2010-2019 (10 years)

NDVI: NOT available in either source. Left blank here - fill via GEE
(see fetch_real_historical.py) once `earthengine authenticate` is run.
Until then, train.py can still run on rainfall/temperature/humidity/
soil_moisture -> yield (NDVI excluded from training, OR filled with a
single representative value - see note at bottom).

Output: historical_dataset_real.csv (10 real rows, 2010-2019)
"""
import csv

import pandas as pd

# --- 1. Real rice yield (Belagavi/Belgaum, Kharif) ---
yield_df = pd.read_csv("crop_yield_district_belagavi.csv")
yield_df.columns = [c.strip() for c in yield_df.columns]
for c in ["State_Name", "District_Name", "Season", "Crop"]:
    yield_df[c] = yield_df[c].astype(str).str.strip()

bel = yield_df[
    (yield_df["Crop"] == "Rice")
    & (yield_df["Season"] == "Kharif")
]

# yield column has duplicate rows in t/ha and q/ha; keep t/ha (smaller, <10)
bel_tha = bel[bel["yield"] < 10][["Crop_Year", "yield"]].drop_duplicates()
yield_by_year = dict(zip(bel_tha["Crop_Year"], bel_tha["yield"]))

print(f"Real yield data (t/ha) for {len(yield_by_year)} years:")
for y, v in sorted(yield_by_year.items()):
    print(f"  {y}: {v:.3f}")

# --- 2. Real NASA POWER weather (exact field coords) ---
nasa = pd.read_csv("nasa_power_belagavi_full.csv", skiprows=15)
nasa.columns = [c.strip() for c in nasa.columns]

kharif_months = ["JUN", "JUL", "AUG", "SEP", "OCT"]

climate_by_year = {}
for year in nasa["YEAR"].unique():
    year = int(year)
    rows = {}
    for param in ["PRECTOTCORR_SUM", "T2M", "RH2M", "GWETROOT"]:
        sub = nasa[(nasa["PARAMETER"] == param) & (nasa["YEAR"] == year)]
        if sub.empty:
            continue
        vals = [sub.iloc[0][m] for m in kharif_months]
        rows[param] = vals

    if not rows:
        continue

    # Rainfall: PRECTOTCORR_SUM is mm/day summed-per-month already per NASA POWER
    # monthly product -> sum across kharif months = total kharif rainfall (mm)
    rainfall = sum(rows["PRECTOTCORR_SUM"])
    temperature = sum(rows["T2M"]) / len(rows["T2M"])
    humidity = sum(rows["RH2M"]) / len(rows["RH2M"])
    soil_moisture = (sum(rows["GWETROOT"]) / len(rows["GWETROOT"])) * 100  # fraction -> %

    climate_by_year[year] = {
        "rainfall": round(rainfall, 1),
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "soil_moisture": round(soil_moisture, 1),
    }

print(f"\nReal NASA POWER climate data for {len(climate_by_year)} years (2010-2024)")

# --- 3. Merge on overlapping years ---
rows = []
for year in sorted(set(yield_by_year) & set(climate_by_year)):
    c = climate_by_year[year]
    rows.append({
        "year": year,
        "rainfall": c["rainfall"],
        "temperature": c["temperature"],
        "humidity": c["humidity"],
        "ndvi": "",  # not available from these sources - fill via GEE
        "soil_moisture": c["soil_moisture"],
        "yield": round(float(yield_by_year[year]), 3),
    })

print(f"\nMerged real dataset: {len(rows)} rows (years {rows[0]['year']}-{rows[-1]['year']})")

with open("historical_dataset_real.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=["year", "rainfall", "temperature", "humidity", "soil_moisture", "yield"]
    )
    writer.writeheader()
    for r in rows:
        r2 = {k: v for k, v in r.items() if k != "ndvi"}
        writer.writerow(r2)

print("\nWrote historical_dataset_real.csv (NDVI column dropped - not available)")
print(f"\n{len(rows)} fully real rows (years {rows[0]['year']}-{rows[-1]['year']}).")
print("Small sample size - model will have wide uncertainty. To extend:")
print("  - Run GEE NDVI fetch for 2015-2024 + corresponding NASA POWER years")
print("    once 2015-2019 yield data quality issue is resolved (use a fresh")
print("    yield source for those years, e.g. data.gov.in district reports).")

for r in rows:
    print(r)
