"""Integration facade for FMP provider."""

from src.integrations.market_data.providers.FMP_api.client import FMPClient
from src.integrations.market_data.providers.FMP_api.routes import router

__all__ = ["FMPClient", "router"]
