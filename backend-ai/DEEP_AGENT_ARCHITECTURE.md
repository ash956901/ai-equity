# Deep Agent Architecture (Current)

This document describes the **current** deep-agent implementation used by backend-ai.

## High-level flow

User/API request -> Orchestrator agent (Iris) -> Specialist sub-agents -> Tool layer -> Final synthesis

The orchestrator and sub-agents are built with `deepagents` and use memory/checkpoint
configuration for continuity.

## Core modules

- Orchestrator builder: `src/agents/orchestrator.py`
- Memory + skills config: `src/agents/memory.py`
- Prompt definitions: `src/agents/prompts/`
- Sub-agent registry: `src/agents/subagents/__init__.py`
- Tool implementations: `src/agents/tools/`
- API entrypoint using orchestrator: `src/domains/chat/service.py`

## Sub-agents

Declared in `src/agents/subagents/`:

- `company-analysis`
- `comparison`
- `portfolio`
- `news-sentiment`
- `doc-insight`

Each sub-agent defines:

- `name`
- `description`
- `system_prompt`
- `tools`

## Memory model

`src/agents/memory.py` configures:

- `StoreBackend` for persistent `/memories/` paths
- `StateBackend` for ephemeral state
- `MemorySaver` checkpointer for thread/session continuity
- skill seeding from `src/agents/skills/*/SKILL.md`

## API usage

Primary runtime path:

- `POST /chat/query` -> `src/domains/chat/routes.py` -> `src/domains/chat/service.py`

The service builds/uses the orchestrator via `build_research_agent()` and stores chat
messages in DB (`ChatSession`, `ChatMessage`).

## Notes

- This backend no longer uses the old `src/deep_research` package layout.
- If architecture changes again, update this file in the same PR to avoid drift.
