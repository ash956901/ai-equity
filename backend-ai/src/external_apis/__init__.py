"""External data API integrations (FMP, FRED, NewsAPI, NewsDataIO, Upstox, Kite)."""

from .FMP_api.routes import router as fmp_router
from .FRED_api.routes import router as fred_router
from .Upstox_api.routes import router as upstox_router
from .NewsAPI.routes import router as news_router
from .NewsDataIO.routes import router as newsdata_router
from .Kite_api.routes import router as kite_router

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
