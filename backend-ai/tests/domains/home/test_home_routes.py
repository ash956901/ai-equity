"""Route smoke tests for /home/personalized."""

from __future__ import annotations

from datetime import datetime

from src.domains.home import routes as home_routes


class _StubHomeService:
    def __init__(self, db):
        self.db = db

    def get_personalized(self, user):
        return {
            "user": {
                "id": str(user.id),
                "username": user.username,
                "expertise_level": user.expertise_level,
                "default_chart_range": "1Y",
            },
            "watchlist_companies": [
                {
                    "company_id": "c1",
                    "name": "Reliance",
                    "ticker_nse": "RELIANCE",
                    "ticker_bse": "500325",
                    "sector": "Energy",
                    "industry": "Oil & Gas Refining",
                    "market_cap_inr": 1_950_000,
                }
            ],
            "holdings_companies": [
                {
                    "company_id": "c2",
                    "name": "TCS",
                    "ticker_nse": "TCS",
                    "ticker_bse": "532540",
                    "sector": "Information Technology",
                    "industry": "IT Services",
                    "market_cap_inr": 1_420_000,
                    "quantity": 12.0,
                }
            ],
            "asymmetric_feed": [
                {
                    "company_id": "c3",
                    "name": "Castrol India",
                    "ticker_nse": "CASTROLIND",
                    "ticker_bse": None,
                    "sector": "Energy",
                    "industry": "Lubricants",
                    "market_cap_inr": 18_000,
                    "theme": "data_centre_lubricants",
                    "impact_score": 0.7,
                    "exposure_type": "second_order",
                    "reasoning": "Specialty coolants used by hyperscale data centres.",
                }
            ],
            "timeline_recent": [
                {
                    "filing_id": "f1",
                    "company_id": "c1",
                    "company_name": "Reliance",
                    "ticker_nse": "RELIANCE",
                    "filing_type": "Quarterly_Results",
                    "filing_date": "2026-04-30",
                    "summary": "Q4 PAT up 12% YoY on retail margin expansion.",
                }
            ],
            "suggestions": [],
            "generated_at": datetime.utcnow().isoformat(),
        }


def test_home_personalized_returns_all_sections(
    monkeypatch, make_authed_client, fake_user
):
    monkeypatch.setattr(home_routes, "HomeService", _StubHomeService)
    client = make_authed_client(router=home_routes.router, user=fake_user)

    resp = client.get("/home/personalized")
    assert resp.status_code == 200
    body = resp.json()

    assert body["user"]["id"] == str(fake_user.id)
    assert len(body["watchlist_companies"]) == 1
    assert body["watchlist_companies"][0]["ticker_nse"] == "RELIANCE"
    assert body["holdings_companies"][0]["quantity"] == 12.0
    assert body["asymmetric_feed"][0]["theme"] == "data_centre_lubricants"
    assert body["asymmetric_feed"][0]["exposure_type"] == "second_order"
    assert body["timeline_recent"][0]["filing_type"] == "Quarterly_Results"
    assert "generated_at" in body


def test_home_requires_auth(make_anon_client):
    """Hitting /home/personalized without an Authorization header → 401."""
    client = make_anon_client(router=home_routes.router)
    resp = client.get("/home/personalized")
    assert resp.status_code == 401
