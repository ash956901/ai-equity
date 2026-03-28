"""Integration facade for NewsData.io provider."""

from src.integrations.market_data.providers.NewsDataIO.client import NewsDataIOClient
from src.integrations.market_data.providers.NewsDataIO.routes import router

__all__ = ["NewsDataIOClient", "router"]
