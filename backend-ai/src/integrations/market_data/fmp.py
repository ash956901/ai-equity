"""Compatibility facade for FMP integration package."""

from src.external_apis.FMP_api.client import FMPClient
from src.external_apis.FMP_api.routes import router

__all__ = ["FMPClient", "router"]
