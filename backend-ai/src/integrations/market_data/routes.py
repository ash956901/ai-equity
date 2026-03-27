"""Router exports for external market-data providers.

This module is the integration-layer import target for app router wiring.
It currently proxies legacy `src.external_apis` routers to preserve behavior.
"""

from src.external_apis.FMP_api.routes import router as fmp_router
from src.external_apis.FRED_api.routes import router as fred_router
from src.external_apis.Kite_api.routes import router as kite_router
from src.external_apis.NewsAPI.routes import router as news_router
from src.external_apis.NewsDataIO.routes import router as newsdata_router
from src.external_apis.Upstox_api.routes import router as upstox_router

ALL_EXTERNAL_ROUTERS = [
    fmp_router,
    fred_router,
    upstox_router,
    news_router,
    newsdata_router,
    kite_router,
]

__all__ = [
    "fmp_router",
    "fred_router",
    "upstox_router",
    "news_router",
    "newsdata_router",
    "kite_router",
    "ALL_EXTERNAL_ROUTERS",
]
