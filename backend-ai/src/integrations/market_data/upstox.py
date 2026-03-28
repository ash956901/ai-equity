"""Integration facade for Upstox provider."""

from src.integrations.market_data.providers.Upstox_api.client import UpstoxClient
from src.integrations.market_data.providers.Upstox_api.routes import router

__all__ = ["UpstoxClient", "router"]
