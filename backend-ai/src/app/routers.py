"""Router registration helpers."""

from fastapi import FastAPI

from src.domains.alerts import alerts_router
from src.domains.chat import chat_router, upload_router
from src.domains.companies import companies_router
from src.domains.compare import compare_router
from src.domains.news import news_router
from src.domains.portfolio import portfolio_router
from src.domains.screens import screens_router
from src.domains.timeline import timeline_router
from src.domains.users import user_router
from src.domains.watchlists import watchlists_router
from src.integrations.market_data import ALL_EXTERNAL_ROUTERS


def register_routers(app: FastAPI) -> None:
    """Attach all API routers to the application."""
    app.include_router(chat_router)
    app.include_router(upload_router)
    app.include_router(companies_router)
    app.include_router(portfolio_router)
    app.include_router(news_router)
    app.include_router(compare_router)
    app.include_router(alerts_router)
    app.include_router(watchlists_router)
    app.include_router(timeline_router)
    app.include_router(screens_router)
    app.include_router(user_router)

    for external_router in ALL_EXTERNAL_ROUTERS:
        app.include_router(external_router)
