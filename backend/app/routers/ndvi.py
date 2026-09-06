"""
ndvi.py
========
NDVI endpoints backed by gee_service (real Sentinel-2 via GEE, or demo
fallback). Provides current NDVI, weekly timeseries (PRD 5.1), and a
heatmap tile URL for the frontend map overlay.
"""
from fastapi import APIRouter

from app.config import settings
from app.services import gee_service
from app.schemas import NdviCurrentOut, NdviHeatmapOut, NdviTimeseriesPoint

router = APIRouter(prefix="/ndvi", tags=["ndvi"])


@router.get("/current", response_model=NdviCurrentOut)
def current_ndvi():
    return gee_service.get_current_ndvi()


@router.get("/timeseries", response_model=list[NdviTimeseriesPoint])
def ndvi_timeseries(weeks: int = 12):
    return gee_service.get_ndvi_timeseries(weeks=weeks)


@router.get("/heatmap", response_model=NdviHeatmapOut)
def ndvi_heatmap():
    tile_url = gee_service.get_ndvi_heatmap_tile_url()
    return {
        "tile_url": tile_url,
        "field_center": {
            "lat": settings.FIELD_CENTER_LAT,
            "lon": settings.FIELD_CENTER_LON,
        },
        "available": tile_url is not None,
    }
