"""Grow the causal SectorExposure graph by mining commodity dependencies from
enriched filings.

The FilingEnricher already extracts ``causal_signals`` (supply-chain
dependencies, external triggers, cost-sensitivity areas) from each filing. When
a company's own filing says e.g. "natural gas is our primary feedstock", that is
strong, first-party evidence that the company's *sector* is exposed to that
commodity — so we add a ``SectorExposure`` edge tagged ``source='filing_mined'``.

This turns the hand-seeded 31-edge graph into one that grows as filings are
ingested, while preserving provenance (seed vs mined) so the grounding layer can
weight them if needed.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Free-text dependency terms → tracked commodity symbols (CommodityPrice.symbol).
_COMMODITY_ALIASES: dict[str, list[str]] = {
    "NATURAL_GAS_USD": ["natural gas", "lng", "gas feedstock", "rng", "regasified"],
    "BRENT_CRUDE_USD": ["crude", "brent", "petroleum", "petrol", "diesel", "naphtha", "fuel oil"],
    "WTI_USD": ["wti"],
    "COAL_USD": ["coal", "coking coal", "thermal coal"],
    "JET_FUEL_USD": ["jet fuel", "atf", "aviation turbine"],
    "XAU": ["gold", "bullion"],
    "XAG": ["silver"],
    "copper": ["copper"],
    "aluminum": ["aluminium", "aluminum", "bauxite", "alumina"],
    "sugar_11": ["sugar", "sugarcane", "sugar cane", "ethanol"],
}

# Signal lists that describe input/cost dependencies (commodity up → margin down).
_SIGNAL_KEYS = (
    "supply_chain_dependencies",
    "external_triggers",
    "cost_sensitivity_areas",
    "hidden_exposure_sectors",
)


def _match_commodities(text: str) -> set[str]:
    lowered = text.lower()
    return {
        symbol
        for symbol, aliases in _COMMODITY_ALIASES.items()
        if any(alias in lowered for alias in aliases)
    }


def _signal_text(signals: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in _SIGNAL_KEYS:
        value = signals.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, str):
            parts.append(value)
    return " ".join(parts)


def mine_sector_exposures_from_filings(db: Session) -> dict[str, Any]:
    """Scan enriched filings and add/extend SectorExposure edges from their
    commodity dependencies. Idempotent: existing edges only gain new companies.
    """
    from src.db.models import Company, Filing, SectorExposure

    filings = db.query(Filing).filter(Filing.metadata_.isnot(None)).all()

    scanned = 0
    edges_added = 0
    companies_linked = 0

    for filing in filings:
        meta = filing.metadata_ or {}
        signals = meta.get("causal_signals") or {}
        if not signals:
            continue

        company = db.query(Company).filter(Company.id == filing.company_id).first()
        if not company or not company.sector:
            continue

        commodities = _match_commodities(_signal_text(signals))
        if not commodities:
            continue
        scanned += 1

        for commodity in commodities:
            existing = (
                db.query(SectorExposure)
                .filter(
                    SectorExposure.sector == company.sector,
                    SectorExposure.commodity == commodity,
                )
                .first()
            )
            if existing:
                companies = list(existing.affected_companies or [])
                if company.name not in companies:
                    companies.append(company.name)
                    existing.affected_companies = companies
                    companies_linked += 1
                continue

            db.add(
                SectorExposure(
                    sector=company.sector,
                    commodity=commodity,
                    dependency_type="input_cost",
                    impact_direction="negative",  # input cost up → margin down
                    impact_magnitude="medium",
                    affected_companies=[company.name],
                    is_active=True,
                    source="filing_mined",
                )
            )
            edges_added += 1

    db.commit()
    result = {
        "filings_scanned": scanned,
        "edges_added": edges_added,
        "companies_linked": companies_linked,
    }
    logger.info("Causal graph mining: %s", result)
    return result
