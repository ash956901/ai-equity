"""Integration facade for NewsAPI provider."""

from src.integrations.market_data.providers.NewsAPI.client import NewsAPIClient
from src.integrations.market_data.providers.NewsAPI.routes import router

__all__ = ["NewsAPIClient", "router"]
