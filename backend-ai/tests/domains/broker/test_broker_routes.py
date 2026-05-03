"""Route smoke tests for /broker/* — Zerodha OAuth start + sync ownership."""

from __future__ import annotations

from uuid import uuid4

from src.domains.broker import routes as broker_routes


class _StubPortfolio:
    def __init__(self, *, id, user_id, broker="zerodha"):
        self.id = id
        self.user_id = user_id
        self.broker = broker
        self.broker_account_id = "kite_user:abc.token"


class _StubQuery:
    def __init__(self, portfolio):
        self._portfolio = portfolio

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._portfolio


class _StubDB:
    def __init__(self, portfolio=None):
        self._portfolio = portfolio

    def query(self, _model):
        return _StubQuery(self._portfolio)


class _StubBrokerService:
    sync_called_with = None
    callback_called_with = None

    def __init__(self, db):
        self.db = db

    def get_zerodha_login_url(self):
        return {"login_url": "https://kite.zerodha.com/connect/login?v=3&api_key=stub"}

    def handle_zerodha_callback(self, *, user_id, request_token):
        _StubBrokerService.callback_called_with = {
            "user_id": str(user_id),
            "request_token": request_token,
        }
        return {
            "portfolio_id": "p-1",
            "kite_user_id": "ABC123",
            "user_name": "Tester",
        }

    def sync_portfolio(self, portfolio_id):
        _StubBrokerService.sync_called_with = str(portfolio_id)
        return {
            "portfolio_id": str(portfolio_id),
            "broker": "zerodha",
            "synced": 5,
            "skipped": 1,
        }


def test_zerodha_login_url(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(broker_routes, "BrokerService", _StubBrokerService)
    client = make_authed_client(router=broker_routes.router, user=fake_user)

    resp = client.get("/broker/zerodha/login-url")
    assert resp.status_code == 200
    assert resp.json()["login_url"].startswith("https://kite.zerodha.com/")


def test_zerodha_callback_post_self_only(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(broker_routes, "BrokerService", _StubBrokerService)
    client = make_authed_client(router=broker_routes.router, user=fake_user)

    # Self → 200.
    resp = client.post(
        "/broker/zerodha/callback",
        json={"user_id": str(fake_user.id), "request_token": "tok-abc"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["portfolio_id"] == "p-1"
    assert _StubBrokerService.callback_called_with["request_token"] == "tok-abc"

    # Cross-account → 403 from assert_self.
    other = uuid4()
    resp = client.post(
        "/broker/zerodha/callback",
        json={"user_id": str(other), "request_token": "tok-xyz"},
    )
    assert resp.status_code == 403


def test_sync_portfolio_owner_only(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(broker_routes, "BrokerService", _StubBrokerService)
    portfolio = _StubPortfolio(id="p-1", user_id=fake_user.id)
    db = _StubDB(portfolio=portfolio)

    client = make_authed_client(
        router=broker_routes.router, user=fake_user, db=db
    )
    resp = client.post(f"/broker/portfolios/{portfolio.id}/sync")
    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 5
    assert _StubBrokerService.sync_called_with == "p-1"


def test_sync_portfolio_blocks_non_owner(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(broker_routes, "BrokerService", _StubBrokerService)
    other_user_id = uuid4()
    portfolio = _StubPortfolio(id="p-2", user_id=other_user_id)
    db = _StubDB(portfolio=portfolio)

    client = make_authed_client(
        router=broker_routes.router, user=fake_user, db=db
    )
    resp = client.post(f"/broker/portfolios/{portfolio.id}/sync")
    assert resp.status_code == 403
    assert "Not your portfolio" in resp.text


def test_sync_portfolio_404_when_missing(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(broker_routes, "BrokerService", _StubBrokerService)
    db = _StubDB(portfolio=None)
    client = make_authed_client(router=broker_routes.router, user=fake_user, db=db)
    resp = client.post("/broker/portfolios/nonexistent/sync")
    assert resp.status_code == 404
