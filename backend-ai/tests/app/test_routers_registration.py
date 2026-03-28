"""Tests for application router registration."""

from src.app.factory import create_app


def test_app_registers_core_and_external_routes():
    app = create_app()
    paths = {route.path for route in app.routes}

    expected = {
        "/health",
        "/chat/query",
        "/chat/upload",
        "/companies/",
        "/compare/",
        "/portfolios/",
        "/alerts/",
        "/watchlists/",
        "/timeline/",
        "/screens/",
        "/users/{user_id}",
        "/fmp/quote/{symbol}",
        "/fred/series/{series_id}",
        "/news/headlines",
        "/newsdata/latest",
        "/upstox/user/profile",
        "/kite/quote/ltp",
    }

    for path in expected:
        assert path in paths
