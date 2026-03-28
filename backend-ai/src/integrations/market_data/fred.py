"""Integration facade for FRED provider."""

from src.integrations.market_data.providers.FRED_api.client import FREDClient
from src.integrations.market_data.providers.FRED_api.routes import router

__all__ = ["FREDClient", "router"]
