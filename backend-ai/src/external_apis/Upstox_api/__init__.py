"""Compatibility wrapper for legacy Upstox external package."""

from src.integrations.market_data.providers.Upstox_api.client import UpstoxClient
from src.integrations.market_data.providers.Upstox_api.models import *  # noqa: F401,F403

__all__ = ["UpstoxClient"]
