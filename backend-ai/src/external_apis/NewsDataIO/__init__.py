"""Compatibility wrapper for legacy NewsData.io external package."""

from src.integrations.market_data.providers.NewsDataIO.client import NewsDataIOClient
from src.integrations.market_data.providers.NewsDataIO.routes import router

__version__ = "1.0.0"

__all__ = ["NewsDataIOClient", "router"]
