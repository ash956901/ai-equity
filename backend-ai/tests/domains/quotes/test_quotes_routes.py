"""Route smoke tests for /quotes/{ticker}, /candles, /peers."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.db.database import get_db
from src.domains.auth.dependencies import optional_user
from src.domains.quotes import routes as quotes_routes


class _StubQuotesService:
    def __init__(self, db):
        self.db = db

    def get_quote(self, ticker):
        ticker_u = ticker.upper()
        if ticker_u == "UNKNOWN":
            return {"ticker": ticker_u, "name": None, "company_id": None, "error": "Unknown ticker"}
        return {
            "ticker": ticker_u,
            "name": "Reliance Industries",
            "company_id": "11111111-1111-1111-1111-111111111111",
            "exchange": "NSE",
            "sector": "Energy",
            "industry": "Oil & Gas Refining",
            "last_price": 2845.5,
            "change_pct": 1.4,
            "open": 2810.0,
            "prev_close": 2806.0,
            "day_high": 2860.0,
            "day_low": 2802.5,
            "volume": 4_120_000,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_candles(self, *, ticker, rng, interval):
        return {
            "ticker": ticker.upper(),
            "exchange": "NSE",
            "range": rng,
            "interval": interval or "1d",
            "source": "yfinance",
            "ohlcv": [
                {"t": "2024-01-01T00:00:00Z", "o": 100, "h": 105, "l": 99, "c": 103, "v": 1_000_000},
                {"t": "2024-01-02T00:00:00Z", "o": 103, "h": 108, "l": 102, "c": 107, "v": 1_200_000},
            ],
            "company_id": "11111111-1111-1111-1111-111111111111",
        }

    def get_peers(self, ticker, *, limit):
        return [
            {
                "company_id": "22222222-2222-2222-2222-222222222222",
                "name": "Indian Oil Corporation",
                "ticker_nse": "IOC",
                "ticker_bse": None,
                "sector": "Energy",
                "industry": "Oil & Gas Refining",
                "market_cap_inr": 240_000,
                "pe_ratio": 6.4,
                "roe": 0.18,
            }
        ]


def _make_client(monkeypatch):
    monkeypatch.setattr(quotes_routes, "QuotesDomainService", _StubQuotesService)
    app = FastAPI()

    def _fake_get_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_get_db
    # /quotes/* uses optional_user — return None to simulate an anonymous request.
    app.dependency_overrides[optional_user] = lambda: None
    app.include_router(quotes_routes.router)
    return TestClient(app)


def test_get_quote_known_ticker(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.get("/quotes/RELIANCE")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "RELIANCE"
    assert body["name"] == "Reliance Industries"
    assert body["last_price"] == 2845.5
    assert body["change_pct"] > 0


def test_get_quote_unknown_ticker(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.get("/quotes/UNKNOWN")
    assert resp.status_code == 200  # service is permissive; surfaces error in body
    body = resp.json()
    assert body["error"] == "Unknown ticker"


def test_get_candles_default_range(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.get("/quotes/RELIANCE/candles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["range"] == "1Y"
    assert body["source"] == "yfinance"
    assert len(body["ohlcv"]) == 2
    assert body["ohlcv"][0]["o"] == 100


def test_get_candles_explicit_range(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.get("/quotes/RELIANCE/candles?range=1M&interval=1d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["range"] == "1M"
    assert body["interval"] == "1d"


def test_get_peers(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.get("/quotes/RELIANCE/peers?limit=8")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["ticker_nse"] == "IOC"
    assert body[0]["industry"] == "Oil & Gas Refining"
