"""
Upstox API Module for Indian financial market data
Supports NSE, BSE, MCX, NFO, CDS exchanges
"""
from .client import UpstoxClient
from .models import *

__all__ = ["UpstoxClient"]
