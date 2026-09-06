"""
gee_service.py
================
Provides NDVI data for the fixed Belagavi field using Google Earth Engine
(Sentinel-2 imagery), with a cached/demo fallback when GEE is not yet
authenticated (GEE_ENABLED=false in .env).

Field polygon: ~1km x 1km box centered at (FIELD_CENTER_LAT, FIELD_CENTER_LON)

Cloud-cover cascade: Sentinel-2's 5-day revisit cycle means the default
30-day lookback usually finds a clear (<40% cloud) image, but during the
Karnataka kharif monsoon (Jun-Oct) it is common to find zero cloud-free
acquisitions in any given 30-day window - this is a known, paper-documented
operational constraint, not a bug. Rather than dropping straight to demo
data the moment the default window comes up empty, NDVI queries widen the
lookback window in stages (30 -> 90 -> 180 days) until a cloud-free image
is found, and report both the acquisition date and how many days back it
was found - so a live-but-stale monsoon reading is clearly distinguishable
from a fresh one, and from the demo fallback (which is only used if even
180 days finds nothing).
"""
import datetime
import logging
import random

from app.config import settings

logger = logging.getLogger(__name__)

_ee_initialized = False
_ee = None

# Cascading lookback windows (days) tried in order until a cloud-free
# Sentinel-2 acquisition is found. See module docstring.
_LOOKBACK_CASCADE_DAYS = [30, 90, 180]


def _get_field_geometry():
    """Returns the ~1km x 1km field polygon as an ee.Geometry."""
    delta = 0.0045  # roughly 500m at this latitude
    lat, lon = settings.FIELD_CENTER_LAT, settings.FIELD_CENTER_LON
    return _ee.Geometry.Rectangle([lon - delta, lat - delta, lon + delta, lat + delta])


def init_gee():
    """
    Initializes the Earth Engine API using the configured GCP project.
    Must be called once at app startup. Safe to call even if GEE_ENABLED
    is false (it will be a no-op).
    """
    global _ee_initialized, _ee

    if not settings.GEE_ENABLED:
        logger.info("GEE_ENABLED=false -> using demo/cached NDVI data")
        return False

    try:
        import ee
        ee.Initialize(project=settings.GEE_PROJECT_ID)
        _ee = ee
        _ee_initialized = True
        logger.info(f"Earth Engine initialized for project {settings.GEE_PROJECT_ID}")
        return True
    except Exception as e:
        logger.warning(f"Failed to initialize Earth Engine: {e}. Falling back to demo NDVI.")
        return False


def _find_clearest_image(field):
    """
    Tries each window in _LOOKBACK_CASCADE_DAYS in order, returning the
    least-cloudy image found in the first window that has any cloud-free
    (<40%) acquisition, along with how many days back that window reached.

    Returns:
        (image, lookback_days) tuple, or (None, None) if no cloud-free
        image was found even at the widest window.
    """
    end = datetime.date.today()

    for lookback_days in _LOOKBACK_CASCADE_DAYS:
        start = end - datetime.timedelta(days=lookback_days)

        collection = (
            _ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate(start.isoformat(), end.isoformat())
            .filterBounds(field)
            .filter(_ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )

        if collection.size().getInfo() > 0:
            if lookback_days > _LOOKBACK_CASCADE_DAYS[0]:
                logger.info(
                    f"No cloud-free Sentinel-2 image in default "
                    f"{_LOOKBACK_CASCADE_DAYS[0]}-day window; found one at "
                    f"{lookback_days}-day lookback (likely monsoon cloud cover)."
                )
            return collection.first(), lookback_days

    return None, None


def get_current_ndvi():
    """
    Returns the most recent NDVI value for the field, computed from the
    least-cloudy available Sentinel-2 image found via the lookback cascade
    (see module docstring). During persistent cloud cover (e.g. kharif
    monsoon), this may be a wider window than the default 30 days - the
    response's `lookback_days` field reports exactly how far back it had
    to search, so a live-but-stale reading is distinguishable from a fresh
    one.

    Returns:
        dict with keys: ndvi (float 0-1), date (ISO string), source (str),
        lookback_days (int)
    """
    if _ee_initialized:
        try:
            field = _get_field_geometry()
            image, lookback_days = _find_clearest_image(field)

            if image is None:
                logger.warning(
                    f"No cloud-free Sentinel-2 image found within "
                    f"{_LOOKBACK_CASCADE_DAYS[-1]} days. Falling back to demo value."
                )
                return _demo_ndvi_current()

            ndvi_img = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
            value = ndvi_img.reduceRegion(
                reducer=_ee.Reducer.mean(), geometry=field, scale=10
            ).get("NDVI").getInfo()

            image_date = _ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()

            return {
                "ndvi": round(float(value), 3),
                "date": image_date,
                "source": "sentinel-2-live",
                "lookback_days": lookback_days,
            }
        except Exception as e:
            logger.warning(f"GEE live NDVI fetch failed: {e}. Falling back to demo value.")

    return _demo_ndvi_current()


def get_ndvi_timeseries(weeks=12):
    """
    Returns NDVI values for the field over the past `weeks` weeks
    (PRD: weekly or bi-weekly NDVI computation).

    If no cloud-free images fall within the requested window (e.g. during
    the kharif monsoon - see module docstring), the query window widens
    through the same cascade used by get_current_ndvi() so the trend chart
    and the "current NDVI" figure stay consistent with each other rather
    than one showing a real reading and the other silently falling back to
    demo data. The returned window may therefore span more than `weeks`
    weeks; every point returned is still a real Sentinel-2 acquisition.

    Returns:
        list of dicts: [{date, ndvi, source}, ...] ordered oldest -> newest
    """
    if _ee_initialized:
        try:
            field = _get_field_geometry()
            end = datetime.date.today()

            requested_days = weeks * 7
            windows_to_try = [requested_days] + [
                d for d in _LOOKBACK_CASCADE_DAYS if d > requested_days
            ]

            for lookback_days in windows_to_try:
                start = end - datetime.timedelta(days=lookback_days)

                collection = (
                    _ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterDate(start.isoformat(), end.isoformat())
                    .filterBounds(field)
                    .filter(_ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
                    .sort("system:time_start")
                )

                def extract(img):
                    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
                    mean_val = ndvi.reduceRegion(
                        reducer=_ee.Reducer.mean(), geometry=field, scale=10
                    ).get("NDVI")
                    return img.set("ndvi_value", mean_val)

                features = collection.map(extract).getInfo()["features"]

                results = []
                for f in features:
                    props = f["properties"]
                    ts = props.get("system:time_start")
                    ndvi_val = props.get("ndvi_value")
                    if ts is None or ndvi_val is None:
                        continue
                    date_str = datetime.datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                    results.append({"date": date_str, "ndvi": round(float(ndvi_val), 3), "source": "sentinel-2-live"})

                if results:
                    if lookback_days > requested_days:
                        logger.info(
                            f"No cloud-free Sentinel-2 images in requested "
                            f"{weeks}-week window; widened to {lookback_days} days "
                            f"to find {len(results)} real acquisition(s)."
                        )
                    return results
        except Exception as e:
            logger.warning(f"GEE NDVI timeseries fetch failed: {e}. Falling back to demo data.")

    return _demo_ndvi_timeseries(weeks)


def get_ndvi_heatmap_tile_url():
    """
    Returns a URL template for an NDVI heatmap tile layer (for map overlay
    on the frontend), generated from the same clearest-available Sentinel-2
    image found via the lookback cascade used by get_current_ndvi() - so
    the heatmap and the reported NDVI value are always from the same
    acquisition. Returns None if GEE is unavailable (frontend should show a
    static demo heatmap image instead).
    """
    if _ee_initialized:
        try:
            field = _get_field_geometry()
            image, _ = _find_clearest_image(field)

            if image is None:
                return None

            ndvi_img = image.normalizedDifference(["B8", "B4"]).rename("NDVI")

            vis_params = {
                "min": 0.0,
                "max": 0.9,
                "palette": ["d73027", "f46d43", "fdae61", "fee08b", "d9ef8b", "a6d96a", "66bd63", "1a9850"],
            }

            map_id = ndvi_img.getMapId(vis_params)
            return map_id["tile_fetcher"].url_format
        except Exception as e:
            logger.warning(f"GEE heatmap tile fetch failed: {e}.")

    return None


# ---------------------------------------------------------------------------
# Demo / cached fallback data (used when GEE_ENABLED=false or GEE call fails)
# Values calibrated to realistic Belagavi kharif-season paddy NDVI ranges.
# ---------------------------------------------------------------------------

def _demo_ndvi_current():
    return {
        "ndvi": 0.612,
        "date": datetime.date.today().isoformat(),
        "source": "demo-cached",
    }


def _demo_ndvi_timeseries(weeks=12):
    today = datetime.date.today()
    results = []
    base = 0.42
    for i in range(weeks, 0, -1):
        date = today - datetime.timedelta(weeks=i)
        # simulate seasonal growth curve with small noise
        growth = (weeks - i) / weeks
        ndvi = base + growth * 0.35 + random.uniform(-0.02, 0.02)
        ndvi = max(0.1, min(0.9, ndvi))
        results.append({"date": date.isoformat(), "ndvi": round(ndvi, 3), "source": "demo-cached"})
    return results
