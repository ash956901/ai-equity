"""Seed theme→theme `relation_edges` for second-order reasoning.

Run:
    PYTHONPATH=. python scripts/seed_themes.py

The taxonomy itself lives in ``src/agents/prompts/themes.yaml`` and is
loaded by ``src.etl.theme_taxonomy_loader.seed_theme_taxonomy``. This
script only seeds the *graph* relations between themes (e.g. AI drives
Data Centres which drive Cooling and Power Transmission), so the
Discovery subagent can walk these edges to surface second-order effects.

Idempotent: re-running upserts on the composite unique index
(`subject_type, subject_id, predicate, object_type, object_id`).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.postgresql import insert  # noqa: E402

from src.db.database import SessionLocal, init_db  # noqa: E402
from src.db.models import RelationEdge, ThemeTaxonomy  # noqa: E402
from src.etl.theme_taxonomy_loader import seed_theme_taxonomy  # noqa: E402

logger = logging.getLogger(__name__)


# Theme→theme relations used by `find_second_order_effects`. Codes match
# the YAML taxonomy in src/agents/prompts/themes.yaml.
#
# (subject_code, predicate, object_code, weight)
THEME_RELATIONS: list[tuple[str, str, str, float]] = [
    # AI / Data centres / Cloud
    ("ai_data_centres", "drives_demand_for", "ai_inference_hardware", 0.9),
    ("ai_data_centres", "drives_demand_for", "semiconductors", 0.85),
    ("ai_data_centres", "drives_demand_for", "cloud_infrastructure", 0.8),
    ("ai_data_centres", "drives_demand_for", "data_centre_lubricants", 0.85),
    ("ai_data_centres", "drives_demand_for", "cooling_thermal", 0.85),
    ("ai_data_centres", "drives_demand_for", "power_transmission", 0.75),
    ("ai_data_centres", "drives_demand_for", "commercial_reit", 0.55),
    ("cloud_infrastructure", "drives_demand_for", "ai_data_centres", 0.85),
    ("cloud_infrastructure", "amplifies", "cybersecurity", 0.4),
    # EV / battery / minerals
    ("electric_vehicles", "drives_demand_for", "battery_storage", 0.95),
    ("electric_vehicles", "drives_demand_for", "lithium_battery", 0.9),
    ("electric_vehicles", "drives_demand_for", "critical_minerals", 0.85),
    ("electric_vehicles", "drives_demand_for", "power_transmission", 0.55),
    ("electric_vehicles", "drives_demand_for", "cooling_thermal", 0.5),
    ("battery_storage", "depends_on", "lithium_battery", 0.8),
    ("battery_storage", "depends_on", "critical_minerals", 0.7),
    # Renewables ecosystem
    ("renewable_solar", "drives_demand_for", "battery_storage", 0.7),
    ("renewable_solar", "drives_demand_for", "power_transmission", 0.7),
    ("renewable_wind", "drives_demand_for", "power_transmission", 0.7),
    ("green_hydrogen", "depends_on", "renewable_solar", 0.7),
    ("green_hydrogen", "depends_on", "renewable_wind", 0.5),
    # Defence / aerospace / space
    ("defence_indigenisation", "drives_demand_for", "drone_aerospace", 0.7),
    ("defence_indigenisation", "drives_demand_for", "space_economy", 0.5),
    ("space_economy", "depends_on", "semiconductors", 0.5),
    # India macro tail-winds
    ("chinaplus_one", "amplifies", "specialty_chemicals", 0.7),
    ("chinaplus_one", "amplifies", "cdmo_crams", 0.7),
    ("chinaplus_one", "amplifies", "pli_scheme", 0.6),
    ("chinaplus_one", "amplifies", "semiconductors", 0.5),
    ("pli_scheme", "amplifies", "semiconductors", 0.6),
    ("pli_scheme", "amplifies", "battery_storage", 0.6),
    ("pli_scheme", "amplifies", "electric_vehicles", 0.55),
    ("pli_scheme", "amplifies", "drone_aerospace", 0.5),
    # Consumer / discretionary
    ("premiumisation", "amplifies", "travel_hospitality", 0.5),
    ("premiumisation", "amplifies", "india_real_estate", 0.4),
    ("quick_commerce", "drives_demand_for", "logistics_warehousing", 0.7),
    ("rural_consumption", "amplifies", "fertilizer_subsidy", 0.4),
    # Sugar / ethanol
    ("ethanol_blending", "amplifies", "sugar_industry", 0.85),
    # Industrial automation
    ("smart_manufacturing", "depends_on", "industrial_automation", 0.7),
    ("industrial_automation", "depends_on", "semiconductors", 0.4),
    # Financials
    ("rate_sensitive_banks", "amplifies", "fintech_lending", 0.3),
    ("digital_payments", "amplifies", "fintech_lending", 0.5),
    # Healthcare
    ("pharma_us_market", "amplifies", "cdmo_crams", 0.4),
    ("biotech_biologics", "depends_on", "cdmo_crams", 0.4),
    ("genomics_diagnostics", "amplifies", "medtech_devices", 0.3),
    # Cooling generic → DC lubricants (parent/child knowledge graph)
    ("cooling_thermal", "amplifies", "data_centre_lubricants", 0.7),
]


def upsert_theme_relations(session) -> int:
    """Upsert theme→theme edges into relation_edges (idempotent)."""
    written = 0
    for subject, predicate, obj, weight in THEME_RELATIONS:
        stmt = insert(RelationEdge).values(
            subject_type="theme",
            subject_id=subject,
            predicate=predicate,
            object_type="theme",
            object_id=obj,
            weight=weight,
            source="seed_themes",
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "subject_type",
                "subject_id",
                "predicate",
                "object_type",
                "object_id",
            ],
            set_={"weight": stmt.excluded.weight, "source": stmt.excluded.source},
        )
        session.execute(stmt)
        written += 1
    return written


def main() -> None:
    init_db()
    # 1) Ensure taxonomy is loaded from YAML (idempotent).
    taxonomy_stats = seed_theme_taxonomy()

    # 2) Seed theme→theme relation edges.
    session = SessionLocal()
    try:
        n_rel = upsert_theme_relations(session)
        n_themes = session.query(ThemeTaxonomy).count()
        session.commit()
        print(
            f"Themes: {n_themes} active in taxonomy "
            f"(loader created={taxonomy_stats.get('created', 0)}, "
            f"updated={taxonomy_stats.get('updated', 0)}). "
            f"Seeded {n_rel} theme-to-theme relation edges."
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
