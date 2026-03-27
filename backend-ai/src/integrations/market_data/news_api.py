"""Compatibility facade for NewsAPI integration package."""

from src.external_apis.NewsAPI.client import NewsAPIClient
from src.external_apis.NewsAPI.routes import router

__all__ = ["NewsAPIClient", "router"]
