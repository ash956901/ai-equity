"""Long-term memory and skills configuration for the deep agent orchestrator.

Uses CompositeBackend to route:
  /memories/*  -> StoreBackend (persistent across threads / sessions)
  everything else -> StateBackend (ephemeral, single thread)

Skills are pre-loaded into the store so every thread can discover them via
progressive disclosure.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from src.config import get_settings

logger = logging.getLogger(__name__)

_store: InMemoryStore | None = None
_checkpointer: MemorySaver | None = None

SKILLS_DIR = Path(__file__).parent / "skills"
SKILLS_VIRTUAL_ROOT = "/skills/"


def _get_store():
    """Return a singleton store instance.

    Uses InMemoryStore for local development. For production, swap with
    ``PostgresStore`` backed by the same DATABASE_URL.
    """
    global _store
    if _store is None:
        settings = get_settings()
        if settings.app_env == "production":
            try:
                from langgraph.store.postgres import PostgresStore

                ctx = PostgresStore.from_conn_string(settings.database_url)
                _store = ctx.__enter__()
                _store.setup()
                logger.info("Using PostgresStore for long-term memory")
            except Exception:
                logger.warning(
                    "PostgresStore unavailable, falling back to InMemoryStore"
                )
                _store = InMemoryStore()
        else:
            _store = InMemoryStore()
            logger.info("Using InMemoryStore for long-term memory (dev mode)")
        _seed_skills(_store)
    return _store


def _get_checkpointer():
    """Return a singleton checkpointer for conversation continuity."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def _seed_skills(store: Any) -> None:
    """Pre-populate the store with SKILL.md files from disk.

    Each skill lives under ``src/agents/skills/<name>/SKILL.md`` on disk and is
    stored at ``/skills/<name>/SKILL.md`` in the store so the agent can find it
    via the ``skills=["/skills/"]`` parameter.
    """
    if not SKILLS_DIR.is_dir():
        logger.warning("Skills directory not found: %s", SKILLS_DIR)
        return

    loaded = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        virtual_path = f"/skills/{skill_dir.name}/SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        store.put(
            namespace=("filesystem",),
            key=virtual_path,
            value=create_file_data(content),
        )
        loaded += 1
        logger.debug("Loaded skill: %s -> %s", skill_dir.name, virtual_path)

    logger.info("Seeded %d skill(s) into the store", loaded)


def make_backend(runtime):
    """Factory passed to ``create_deep_agent(backend=...)``.

    Routes ``/memories/*`` to persistent StoreBackend; everything else
    (including ``/skills/``) goes through StoreBackend as well since we
    pre-seeded skills there.
    """
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/memories/": StoreBackend(runtime),
        },
    )


def get_memory_config() -> dict[str, Any]:
    """Return the kwargs to pass to ``create_deep_agent`` for memory + skills.

    Returns a dict with keys: ``store``, ``backend``, ``checkpointer``, ``skills``.
    """
    return {
        "store": _get_store(),
        "backend": make_backend,
        "checkpointer": _get_checkpointer(),
        "skills": [SKILLS_VIRTUAL_ROOT],
    }
