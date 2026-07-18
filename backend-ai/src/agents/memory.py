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

_store: Any = None
_checkpointer: Any = None
_pool: Any = None


def _pg_conninfo() -> str | None:
    """Return a psycopg3-compatible connection string, or None if unset."""
    url = get_settings().database_url
    if not url:
        return None
    # psycopg3 wants a bare postgresql:// URL, not a SQLAlchemy driver form.
    return url.replace("postgresql+psycopg2://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def _get_pool():
    """Return a shared psycopg3 connection pool for the checkpointer + store.

    ``autocommit`` and ``dict_row`` are required by langgraph's Postgres
    backends; ``prepare_threshold=0`` keeps it compatible with poolers.
    Returns None (callers fall back to in-memory) if a pool can't be opened.
    """
    global _pool
    if _pool is not None:
        return _pool
    conninfo = _pg_conninfo()
    if not conninfo:
        return None
    try:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(
            conninfo=conninfo,
            max_size=20,
            kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0},
            open=True,
        )
        pool.wait(timeout=5.0)
        _pool = pool
    except Exception as e:
        logger.warning("Postgres connection pool unavailable (%s); using in-memory backends", e)
        _pool = None
    return _pool

SKILLS_DIR = Path(__file__).parent / "skills"
SKILLS_VIRTUAL_ROOT = "/skills/"


def _get_store():
    """Return a singleton long-term-memory store.

    Prefers a Postgres-backed store (persists across restarts and is shared
    across workers) and falls back to ``InMemoryStore`` when Postgres is
    unavailable.
    """
    global _store
    if _store is None:
        pool = _get_pool()
        if pool is not None:
            try:
                from langgraph.store.postgres import PostgresStore

                store = PostgresStore(pool)
                store.setup()
                _store = store
                logger.info("Using PostgresStore for long-term memory")
            except Exception as e:
                logger.warning("PostgresStore unavailable (%s), falling back to InMemoryStore", e)
                _store = InMemoryStore()
        else:
            _store = InMemoryStore()
            logger.info("Using InMemoryStore for long-term memory (no Postgres pool)")
        _seed_skills(_store)
    return _store


def _get_checkpointer():
    """Return a singleton checkpointer for conversation continuity.

    Prefers a Postgres-backed checkpointer so session threads survive restarts
    and are shared across workers; falls back to in-process ``MemorySaver``.
    """
    global _checkpointer
    if _checkpointer is None:
        pool = _get_pool()
        if pool is not None:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver

                saver = PostgresSaver(pool)
                saver.setup()
                _checkpointer = saver
                logger.info("Using PostgresSaver checkpointer for session continuity")
            except Exception as e:
                logger.warning("PostgresSaver unavailable (%s), falling back to MemorySaver", e)
                _checkpointer = MemorySaver()
        else:
            _checkpointer = MemorySaver()
            logger.info("Using in-memory MemorySaver checkpointer (no Postgres pool)")
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
