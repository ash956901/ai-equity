"""
FRED API Integration for Federal Reserve Economic Data
Provides access to 700,000+ macroeconomic time series
"""
from .client import FREDClient
from .routes import router

__all__ = ["FREDClient", "router"]
