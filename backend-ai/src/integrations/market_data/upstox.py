"""Compatibility facade for Upstox integration package."""

from src.external_apis.Upstox_api.client import UpstoxClient
from src.external_apis.Upstox_api.routes import router

__all__ = ["UpstoxClient", "router"]
