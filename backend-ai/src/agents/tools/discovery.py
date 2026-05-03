"""Discovery tools: hidden exposure, second-order effects, supply-chain
links, and macro sensitivity for the Discovery / Hidden-Insight subagent.

These tools assume the offline ``ThemeTaggingAgent`` has populated
``company_themes`` (with ``is_asymmetric`` etc.) and that
``relation_edges`` carries both ``company → theme`` (predicate
``exposed_to_theme``) and ``theme → theme`` (predicates
``drives_demand_for | amplifies | depends_on``) edges.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool
from sqlalchemy import desc, func, or_

from src.agents.tools._utils import emit_tool_metric, resolve_company_id
from src.db.database import get_db
from src.db.models import Company, CompanyTheme, RelationEdge


# Predicates that define forward second-order propagation.
FORWARD_PREDICATES = ("drives_demand_for", "amplifies", "depends_on")


@tool
def get_companies_in_theme(
    theme: str,
    min_confidence: float = 0.55,
    exposure_types: Optional[str] = None,
    asymmetric_only: bool = False,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Reverse lookup: which companies are exposed to a given theme?

    Args:
        theme: Theme code (e.g. ``ai_data_centres``,
            ``data_centre_lubricants``, ``green_hydrogen``).
        min_confidence: Drop tags below this confidence.
        exposure_types: Comma-separated filter, e.g.
            ``"direct,derivative,second_order"``.
        asymmetric_only: Surface only Castrol-style non-obvious tags.
        limit: Max rows.
    """
    emit_tool_metric("get_companies_in_theme")
    db = next(get_db())
    try:
        q = (
            db.query(CompanyTheme, Company)
            .join(Company, CompanyTheme.company_id == Company.id)
            .filter(CompanyTheme.is_active.is_(True))
            .filter(CompanyTheme.theme_name == theme)
            .filter(CompanyTheme.confidence_score >= min_confidence)
        )
        if exposure_types:
            allowed = [s.strip() for s in exposure_types.split(",") if s.strip()]
            if allowed:
                q = q.filter(CompanyTheme.exposure_type.in_(allowed))
        if asymmetric_only:
            q = q.filter(CompanyTheme.is_asymmetric.is_(True))
        rows = (
            q.order_by(desc(CompanyTheme.impact_score))
            .limit(limit)
            .all()
        )
        return [
            {
                "company_id": str(c.id),
                "company_name": c.name,
                "ticker_nse": c.ticker_nse,
                "sector": c.sector,
                "industry": c.industry,
                "theme": t.theme_name,
                "exposure_type": t.exposure_type,
                "impact_score": float(t.impact_score) if t.impact_score is not None else None,
                "impact_direction": t.impact_direction,
                "impact_horizon": t.impact_horizon,
                "confidence_score": (
                    float(t.confidence_score) if t.confidence_score is not None else None
                ),
                "is_asymmetric": bool(t.is_asymmetric),
                "evidence_quotes": (t.evidence_quotes or [])[:3],
                "reasoning": (t.reasoning or "")[:400],
            }
            for t, c in rows
        ]
    finally:
        db.close()


def _theme_neighbors(
    db, theme_code: str, max_hops: int
) -> List[Tuple[str, float, List[str]]]:
    """BFS theme→theme edges up to ``max_hops`` hops.

    Returns (theme_code, cumulative_weight, path_predicates).
    """
    visited: Dict[str, Tuple[float, List[str]]] = {theme_code: (1.0, [])}
    frontier: List[Tuple[str, float, List[str]]] = [(theme_code, 1.0, [])]
    for _ in range(max_hops):
        next_frontier: List[Tuple[str, float, List[str]]] = []
        if not frontier:
            break
        edges = (
            db.query(RelationEdge)
            .filter(RelationEdge.subject_type == "theme")
            .filter(RelationEdge.subject_id.in_([n[0] for n in frontier]))
            .filter(RelationEdge.object_type == "theme")
            .filter(RelationEdge.predicate.in_(FORWARD_PREDICATES))
            .all()
        )
        for edge in edges:
            cum_weight, path = next(
                (w, p) for n, w, p in frontier if n == edge.subject_id
            )
            new_w = cum_weight * float(edge.weight or 0.5)
            new_path = path + [f"{edge.subject_id}-{edge.predicate}->{edge.object_id}"]
            existing = visited.get(edge.object_id)
            if existing is None or new_w > existing[0]:
                visited[edge.object_id] = (new_w, new_path)
                next_frontier.append((edge.object_id, new_w, new_path))
        frontier = next_frontier

    return [(code, w, path) for code, (w, path) in visited.items() if code != theme_code]


@tool
def find_second_order_effects(
    theme_or_event: str,
    max_hops: int = 2,
    companies_per_theme: int = 5,
    min_company_confidence: float = 0.55,
) -> Dict[str, Any]:
    """Walk the theme graph to find downstream beneficiaries / sufferers.

    Use this when the user asks "if X plays out, who else benefits?" or
    "what's the second-order impact of an AI infra boom?". Returns a list
    of derived themes (1-2 hops away) and the highest-conviction companies
    tagged to each.

    Args:
        theme_or_event: A theme code (preferred). Names work too.
        max_hops: Edge depth (default 2 — primary + secondary effects).
        companies_per_theme: How many companies to return per derived theme.
        min_company_confidence: Drop weak company tags.
    """
    emit_tool_metric("find_second_order_effects")
    db = next(get_db())
    try:
        # Resolve a theme name to a code if needed by trying an exact
        # match first, else case-insensitive label search via taxonomy.
        from src.db.models import ThemeTaxonomy

        theme_code = theme_or_event
        match = (
            db.query(ThemeTaxonomy)
            .filter(
                or_(
                    ThemeTaxonomy.code == theme_or_event,
                    func.lower(ThemeTaxonomy.label) == theme_or_event.lower(),
                )
            )
            .first()
        )
        if match:
            theme_code = match.code

        neighbors = _theme_neighbors(db, theme_code, max_hops)
        if not neighbors:
            return {
                "seed_theme": theme_code,
                "derived": [],
                "note": "No outbound theme→theme edges. Seed seed_themes.py?",
            }

        derived: List[Dict[str, Any]] = []
        for code, weight, path in sorted(neighbors, key=lambda x: -x[1])[:10]:
            company_rows = (
                db.query(CompanyTheme, Company)
                .join(Company, CompanyTheme.company_id == Company.id)
                .filter(CompanyTheme.is_active.is_(True))
                .filter(CompanyTheme.theme_name == code)
                .filter(CompanyTheme.confidence_score >= min_company_confidence)
                .order_by(desc(CompanyTheme.impact_score))
                .limit(companies_per_theme)
                .all()
            )
            derived.append(
                {
                    "theme_code": code,
                    "propagation_weight": round(weight, 4),
                    "path": path,
                    "companies": [
                        {
                            "company_id": str(c.id),
                            "company_name": c.name,
                            "ticker_nse": c.ticker_nse,
                            "exposure_type": t.exposure_type,
                            "impact_direction": t.impact_direction,
                            "is_asymmetric": bool(t.is_asymmetric),
                            "impact_score": (
                                float(t.impact_score) if t.impact_score is not None else None
                            ),
                        }
                        for t, c in company_rows
                    ],
                }
            )
        return {"seed_theme": theme_code, "derived": derived}
    finally:
        db.close()


@tool
def find_supply_chain_links(
    company_id: str,
    direction: str = "both",
    limit: int = 25,
) -> Dict[str, Any]:
    """Return upstream suppliers and/or downstream customers for a company.

    Args:
        company_id: Company UUID or name/ticker.
        direction: ``upstream`` (suppliers), ``downstream`` (customers),
            or ``both``.
        limit: Max edges per direction.
    """
    emit_tool_metric("find_supply_chain_links")
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return {"error": str(e)}

        result: Dict[str, Any] = {"company_id": str(uid)}

        if direction in ("downstream", "both"):
            downstream = (
                db.query(RelationEdge)
                .filter(RelationEdge.subject_type == "company")
                .filter(RelationEdge.subject_id == str(uid))
                .filter(
                    RelationEdge.predicate.in_(("supplies", "customer_of", "produces"))
                )
                .limit(limit)
                .all()
            )
            result["downstream"] = [
                {
                    "predicate": e.predicate,
                    "object_type": e.object_type,
                    "object_id": e.object_id,
                    "weight": float(e.weight) if e.weight is not None else None,
                    "source": e.source,
                }
                for e in downstream
            ]

        if direction in ("upstream", "both"):
            upstream = (
                db.query(RelationEdge)
                .filter(RelationEdge.object_type == "company")
                .filter(RelationEdge.object_id == str(uid))
                .filter(RelationEdge.predicate.in_(("supplies", "supplier_of")))
                .limit(limit)
                .all()
            )
            result["upstream"] = [
                {
                    "predicate": e.predicate,
                    "subject_type": e.subject_type,
                    "subject_id": e.subject_id,
                    "weight": float(e.weight) if e.weight is not None else None,
                    "source": e.source,
                }
                for e in upstream
            ]

        return result
    finally:
        db.close()


@tool
def get_macro_sensitivity(company_id: str) -> Dict[str, Any]:
    """Return the denormalised macro_sensitivity JSON for a company.

    Populated by offline jobs (rate sensitivity, FX, commodity exposure
    derived from sector_commodity_links and macro_series correlations).
    Falls back to an empty dict when no sensitivity has been computed.
    """
    emit_tool_metric("get_macro_sensitivity")
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return {"error": str(e)}
        c = db.query(Company).filter(Company.id == uid).first()
        if not c:
            return {"error": "company_not_found"}
        return {
            "company_id": str(uid),
            "company_name": c.name,
            "macro_sensitivity": c.macro_sensitivity or {},
            "supply_chain_summary": c.supply_chain_summary or {},
            "thematic_exposure_summary": c.thematic_exposure_summary or {},
        }
    finally:
        db.close()
