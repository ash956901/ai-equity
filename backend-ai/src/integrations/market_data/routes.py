"""Router exports for market-data provider integrations.

App-level wiring should import routers from this module only.
"""

from src.integrations.market_data.fmp import router as fmp_router
from src.integrations.market_data.fred import router as fred_router
from src.integrations.market_data.kite import router as kite_router
from src.integrations.market_data.news_api import router as news_router
from src.integrations.market_data.newsdata_io import router as newsdata_router
from src.integrations.market_data.upstox import router as upstox_router

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
