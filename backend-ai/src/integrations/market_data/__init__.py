"""Market data integration namespace.

Phase 4 migration target for provider routers/clients. Existing
`src.external_apis` modules remain as compatibility sources while app-level
imports move to this namespace.
"""

from src.integrations.market_data.routes import (
    ALL_EXTERNAL_ROUTERS,
    fmp_router,
    fred_router,
    kite_router,
    news_router,
    newsdata_router,
    upstox_router,
)

__all__ = [
    "fmp_router",
    "fred_router",
    "upstox_router",
    "news_router",
    "newsdata_router",
    "kite_router",
    "ALL_EXTERNAL_ROUTERS",
]
