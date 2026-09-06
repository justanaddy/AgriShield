"""
weather.py
===========
Weather endpoints backed by weather_service (real Open-Meteo API).
"""
from fastapi import APIRouter

from app.services import weather_service
from app.schemas import ClimateSummaryOut, CurrentWeatherOut, ForecastDayOut, SeasonalClimateSummaryOut

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current", response_model=CurrentWeatherOut)
async def current_weather():
    return await weather_service.get_current_weather()


@router.get("/forecast", response_model=list[ForecastDayOut])
async def forecast(days: int = 7):
    return await weather_service.get_forecast(days=days)


@router.get("/climate-summary", response_model=ClimateSummaryOut)
async def climate_summary(days: int = 14):
    return await weather_service.get_recent_climate_summary(days=days)


@router.get("/seasonal-summary", response_model=SeasonalClimateSummaryOut)
async def seasonal_summary():
    """
    Season-to-date (Jun-Oct kharif) climate summary - these are the exact
    values used as ML model inputs (rainfall, temperature, humidity).
    """
    return await weather_service.get_seasonal_climate_summary()
