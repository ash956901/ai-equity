"""Route smoke tests for /discovery/* — themes catalogue, theme→companies,
asymmetric feed, neighbours."""

from __future__ import annotations

from src.domains.discovery import routes as discovery_routes


class _StubDiscoveryService:
    def __init__(self, db):
        self.db = db

    def list_themes(self, *, only_with_companies):
        return [
            {
                "code": "ai_data_centres",
                "label": "AI / Data Centres",
                "category": "technology",
                "parent_code": None,
                "description": "Companies riding the AI infra build-out.",
                "keywords": ["ai", "data centre"],
                "company_count": 12,
                "asymmetric_count": 3,
            },
            {
                "code": "data_centre_lubricants",
                "label": "Data-centre Lubricants & Cooling",
                "category": "industrials",
                "parent_code": "ai_data_centres",
                "description": "Specialty lubricants — second-order AI exposure.",
                "keywords": ["coolant", "immersion"],
                "company_count": 2,
                "asymmetric_count": 2,
            },
        ]

    def companies_in_theme(
        self, theme, *, min_confidence, exposure_types, asymmetric_only, limit
    ):
        rows = [
            {
                "company_id": "c1",
                "company_name": "Castrol India",
                "ticker_nse": "CASTROLIND",
                "sector": "Energy",
                "industry": "Lubricants",
                "theme_code": theme,
                "exposure_type": "second_order",
                "impact_score": 0.7,
                "impact_direction": "+",
                "impact_horizon": "medium",
                "confidence_score": 0.78,
                "is_asymmetric": True,
                "evidence_quotes": ["Specialty cooling fluids for hyperscalers."],
                "reasoning": "Castrol manufactures coolants used in DC immersion cooling.",
            }
        ]
        if asymmetric_only:
            return [r for r in rows if r["is_asymmetric"]]
        return rows

    def themes_for_company(self, company_id, *, asymmetric_only, limit):
        return [
            {
                "theme_code": "data_centre_lubricants",
                "exposure_type": "second_order",
                "impact_score": 0.7,
                "impact_direction": "+",
                "impact_horizon": "medium",
                "confidence_score": 0.78,
                "is_asymmetric": True,
                "evidence_quotes": [],
                "reasoning": "Castrol → DC coolants.",
                "detected_at": "2026-04-30T00:00:00",
            }
        ]

    def asymmetric_feed(self, *, theme, sector, min_confidence, limit):
        return [
            {
                "company_id": "c1",
                "company_name": "Castrol India",
                "ticker_nse": "CASTROLIND",
                "sector": "Energy",
                "industry": "Lubricants",
                "theme_code": "data_centre_lubricants",
                "exposure_type": "second_order",
                "impact_score": 0.7,
                "impact_direction": "+",
                "impact_horizon": "medium",
                "confidence_score": 0.78,
                "is_asymmetric": True,
                "evidence_quotes": [],
                "reasoning": "DC immersion cooling supplier.",
                "detected_at": "2026-04-30T00:00:00",
            }
        ]

    def theme_neighbors(self, theme):
        if theme == "no_neighbours":
            return []
        return [
            {
                "predicate": "drives_demand_for",
                "neighbor_code": "data_centre_lubricants",
                "weight": 0.85,
                "source": "seed_themes",
            }
        ]


def test_list_themes(monkeypatch, make_anon_client):
    monkeypatch.setattr(discovery_routes, "DiscoveryService", _StubDiscoveryService)
    client = make_anon_client(router=discovery_routes.router)
    resp = client.get("/discovery/themes")
    assert resp.status_code == 200
    body = resp.json()
    assert any(t["code"] == "ai_data_centres" for t in body)
    asym = next(t for t in body if t["code"] == "data_centre_lubricants")
    assert asym["asymmetric_count"] == 2
    assert asym["parent_code"] == "ai_data_centres"


def test_companies_in_theme_asymmetric_only(monkeypatch, make_anon_client):
    monkeypatch.setattr(discovery_routes, "DiscoveryService", _StubDiscoveryService)
    client = make_anon_client(router=discovery_routes.router)
    resp = client.get(
        "/discovery/themes/data_centre_lubricants/companies?asymmetric_only=true"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["company_name"] == "Castrol India"
    assert body[0]["is_asymmetric"] is True
    assert body[0]["exposure_type"] == "second_order"


def test_themes_for_company(monkeypatch, make_anon_client):
    monkeypatch.setattr(discovery_routes, "DiscoveryService", _StubDiscoveryService)
    client = make_anon_client(router=discovery_routes.router)
    resp = client.get(
        "/discovery/companies/00000000-0000-0000-0000-000000000001/themes"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["theme_code"] == "data_centre_lubricants"


def test_asymmetric_feed(monkeypatch, make_anon_client):
    monkeypatch.setattr(discovery_routes, "DiscoveryService", _StubDiscoveryService)
    client = make_anon_client(router=discovery_routes.router)
    resp = client.get("/discovery/asymmetric?min_confidence=0.6&limit=20")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["is_asymmetric"] is True
    assert body[0]["theme_code"] == "data_centre_lubricants"


def test_theme_neighbours_404_when_empty(monkeypatch, make_anon_client):
    monkeypatch.setattr(discovery_routes, "DiscoveryService", _StubDiscoveryService)
    client = make_anon_client(router=discovery_routes.router)
    resp = client.get("/discovery/themes/no_neighbours/neighbors")
    assert resp.status_code == 404


def test_theme_neighbours_returns_edges(monkeypatch, make_anon_client):
    monkeypatch.setattr(discovery_routes, "DiscoveryService", _StubDiscoveryService)
    client = make_anon_client(router=discovery_routes.router)
    resp = client.get("/discovery/themes/ai_data_centres/neighbors")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["predicate"] == "drives_demand_for"
    assert body[0]["neighbor_code"] == "data_centre_lubricants"
