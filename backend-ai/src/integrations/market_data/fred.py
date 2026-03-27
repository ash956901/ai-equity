"""Compatibility facade for FRED integration package."""

from src.external_apis.FRED_api.client import FREDClient
from src.external_apis.FRED_api.routes import router

__all__ = ["FREDClient", "router"]
