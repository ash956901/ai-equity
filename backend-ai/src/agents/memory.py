"""Long-term memory and skills configuration for the orchestrator.

Uses MemorySaver for conversation continuity and flat-file storage
for persistent memory (/memories/) and skills (/skills/).

No deepagents dependency — all LangGraph-native.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from src.config import get_settings

logger = logging.getLogger(__name__)

_checkpointer: MemorySaver | None = None

SKILLS_DIR = Path(__file__).parent / "skills"


def _ensure_directories():
    """Create memories and skills directories if missing."""
    settings = get_settings()
    base = Path(settings.workflow_runs_dir)
    (base / "memories" / "research_notes").mkdir(parents=True, exist_ok=True)
    (base / "skills").mkdir(parents=True, exist_ok=True)

    # Copy skills from source if skills dir is empty
    target_skills = base / "skills"
    if SKILLS_DIR.is_dir() and not any(target_skills.iterdir()):
        _seed_skills(target_skills)


def _seed_skills(target_dir: Path):
    """Copy skill files from src/agents/skills/ to workflow_runs/skills/."""
    loaded = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        dest = target_dir / skill_dir.name
        dest.mkdir(exist_ok=True)
        (dest / "SKILL.md").write_text(skill_file.read_text(encoding="utf-8"))
        loaded += 1
    logger.info("Seeded %d skill(s) to %s", loaded, target_dir)


def _get_checkpointer():
    """Return a singleton checkpointer for conversation continuity."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def get_memory_config() -> dict[str, Any]:
    """Return checkpointer config for the orchestrator graph.

    Returns a dict with: checkpointer, memories_dir, skills_dir.
    """
    _ensure_directories()
    settings = get_settings()
    base = Path(settings.workflow_runs_dir)

    return {
        "checkpointer": _get_checkpointer(),
        "memories_dir": str(base / "memories"),
        "skills_dir": str(base / "skills"),
    }
