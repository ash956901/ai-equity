"""Broker connect domain (Zerodha Kite first, others stubbed)."""

from src.domains.broker.routes import router as broker_router

__all__ = ["broker_router"]
