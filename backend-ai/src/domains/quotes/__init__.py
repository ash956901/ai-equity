"""Quote / candle / peer domain (broker-app-grade stock data)."""

from src.domains.quotes.routes import router as quotes_router

__all__ = ["quotes_router"]
