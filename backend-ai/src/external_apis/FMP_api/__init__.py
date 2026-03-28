"""Compatibility wrapper for legacy FMP external API package."""

from src.integrations.market_data.providers.FMP_api.client import FMPClient
from src.integrations.market_data.providers.FMP_api.routes import router

__version__ = "1.0.0"

__all__ = ["FMPClient", "router"]
