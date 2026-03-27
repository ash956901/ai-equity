"""
Financial Modeling Prep (FMP) API Integration
Provides comprehensive financial data for equity analysis and AI-driven insights
"""

from .client import FMPClient
from .routes import router

__version__ = "1.0.0"

__all__ = ["FMPClient", "router"]
