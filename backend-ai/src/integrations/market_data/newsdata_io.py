"""Compatibility facade for NewsData.io integration package."""

from src.external_apis.NewsDataIO.client import NewsDataIOClient
from src.external_apis.NewsDataIO.routes import router

__all__ = ["NewsDataIOClient", "router"]
