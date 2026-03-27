"""Market data service namespace.

This namespace will host focused quote/fundamentals/ratios services.
For now it re-exports the existing real-time service to preserve behavior.
"""

from src.services.realtime_data import RealTimeDataService

__all__ = ["RealTimeDataService"]
