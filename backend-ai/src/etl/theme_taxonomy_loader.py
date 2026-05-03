"""Loads the theme YAML taxonomy into the ``theme_taxonomy`` table."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import select

from src.db.database import SessionLocal
from src.db.models import ThemeTaxonomy

logger = logging.getLogger(__name__)

YAML_PATH = Path(__file__).resolve().parents[1] / "agents" / "prompts" / "themes.yaml"


def _load_yaml() -> List[Dict[str, Any]]:
    if not YAML_PATH.exists():
        return []
    try:
        import yaml  # type: ignore
    except ImportError:
        logger.error("PyYAML not installed - cannot load themes.yaml")
        return []
    with YAML_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("themes", []) or []


def seed_theme_taxonomy() -> Dict[str, int]:
    rows = _load_yaml()
    if not rows:
        return {"created": 0, "updated": 0}

    db = SessionLocal()
    created = updated = 0
    try:
        for row in rows:
            code = row.get("code")
            if not code:
                continue
            stmt = select(ThemeTaxonomy).where(ThemeTaxonomy.code == code)
            existing = db.execute(stmt).scalar_one_or_none()
            payload = {
                "code": code,
                "label": row.get("label", code),
                "category": row.get("category"),
                "description": row.get("description"),
                "keywords": row.get("keywords") or [],
                "parent_code": row.get("parent_code"),
                "is_active": True,
            }
            if existing is None:
                db.add(ThemeTaxonomy(**payload))
                created += 1
            else:
                changed = False
                for k, v in payload.items():
                    if getattr(existing, k) != v:
                        setattr(existing, k, v)
                        changed = True
                if changed:
                    updated += 1
        db.commit()
        return {"created": created, "updated": updated}
    finally:
        db.close()


def list_themes() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(ThemeTaxonomy).filter(ThemeTaxonomy.is_active.is_(True)).all()
        return [
            {
                "code": r.code,
                "label": r.label,
                "category": r.category,
                "description": r.description,
                "keywords": r.keywords or [],
                "parent_code": r.parent_code,
            }
            for r in rows
        ]
    finally:
        db.close()
