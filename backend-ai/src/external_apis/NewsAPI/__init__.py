"""Compatibility wrapper for legacy NewsAPI external package."""

from src.integrations.market_data.providers.NewsAPI.client import NewsAPIClient
from src.integrations.market_data.providers.NewsAPI.routes import router

__version__ = "1.0.0"

__all__ = ["NewsAPIClient", "router"]
