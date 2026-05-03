# Planning documents — index

This folder contains both **historical design** (what was originally proposed) and **current state** (what's actually built). New contributors: start with `SHIPPED.md`.

---

## Quick start

1. **[SHIPPED.md](./SHIPPED.md)** — single source of truth for what's actually built today, with file-path evidence. Read this first.
2. **[ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md)** — concise current-state architecture snapshot (11 subagents, auth + quotes + home + discovery domains, Round 2 stack).
3. **[07_round2_broker_grade_plan.md](./07_round2_broker_grade_plan.md)** — the active phased plan with locked architectural decisions and P2 deferred items + triggers.

For end-to-end setup see [`/GETTING_STARTED.md`](../GETTING_STARTED.md). For coding rules see [`/AGENTS.md`](../AGENTS.md). For agent topology see [`/backend-ai/DEEP_AGENT_ARCHITECTURE.md`](../backend-ai/DEEP_AGENT_ARCHITECTURE.md).

---

## Current state

| Document | Purpose |
|---|---|
| **[SHIPPED.md](./SHIPPED.md)** | Round 1 + Round 2 deliverables, with `src/...` paths. Migrations to run, env vars to set, deps to install. |
| [07_round2_broker_grade_plan.md](./07_round2_broker_grade_plan.md) | Locked decisions (D1–D11), P1 workstreams W1–W6, P2 deferred items with triggers, NFRs, Mermaid diagrams. |
| [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) | Concise current architecture summary. |
| [NEXT_ROUND_PROMPT.md](./NEXT_ROUND_PROMPT.md) | Reusable planning brief for the next round of gap analysis. |

---

## Historical design (Round 0 — original proposal, retained for reference)

Each of these now carries a "Status (as of Round 2)" banner pointing at SHIPPED.md when it has diverged.

| Document | Topic |
|---|---|
| [00_architecture_refinement_summary.md](./00_architecture_refinement_summary.md) | Original end-to-end architecture summary |
| [01_database_schema.md](./01_database_schema.md) | Original PostgreSQL schema |
| [02_ingestion_pipelines.md](./02_ingestion_pipelines.md) | Original crawling + ETL design |
| [03_vector_store_strategy.md](./03_vector_store_strategy.md) | Qdrant collection + chunking strategy |
| [04_langgraph_agent_design.md](./04_langgraph_agent_design.md) | Original 5-subagent + Router + Synthesis design |
| [05_cloud_deployment_strategy.md](./05_cloud_deployment_strategy.md) | AWS deployment architecture |
| [06_repo_refactor_migration_map.md](./06_repo_refactor_migration_map.md) | Repo refactor migration map |
| [features.md](./features.md) | Original feature wishlist |
| [chatgpt.txt](./chatgpt.txt) | Initial ChatGPT brainstorm |

---

## Key locked decisions today

(See [07_round2_broker_grade_plan.md](./07_round2_broker_grade_plan.md) for the full table with rationale and reconsider-triggers.)

| # | Decision | Choice |
|---|---|---|
| D1 | ETL orchestrator | Celery + SQS + Redis (OSS, free) |
| D2 | Auth | argon2id + JWT (access 15 min + refresh 30 d, rotation in Redis) |
| D3 | Stock chart data | yfinance → Upstox → FMP, aggressively cached |
| D4 | Charting library | TradingView Lightweight Charts (Apache 2.0) — Recharts in production today |
| D5 | Real-time price | 10s polling now, SSE in P2 |
| D6 | Frontend server-state | TanStack Query |
| D7 | Chat streaming | Deferred to P2 |
| D8 | MCP exposure | Deferred to P2 |
| D9 | Deployment | Docker Compose locally; AWS-ready |
| D10 | New SaaS spend ceiling P1 | ~$50/month |

---

## Implementation status (rolled up)

| Capability | Status |
|---|---|
| Minerva chat (11 subagents, structured output) | ✅ live |
| Discovery / asymmetric feed (theme tagger + subagent + API) | ✅ live |
| Personalised Home + OmniSearch | ✅ live |
| Broker-style stock page (1D/1W/.../MAX, candle/line, peers, Ask-Minerva FAB) | ✅ live |
| Auth (signup / login / refresh / logout / forgot / reset / verify-email) | ✅ live |
| Portfolio CRUD + Zerodha Kite OAuth + holdings sync | ✅ live |
| Alert evaluator + Celery delivery | ✅ live |
| AI Timeline summarizer | ✅ live |
| Visualization service (Plotly PNGs to S3 / local) | ✅ live |
| Observability (`/health`, `/ready`, `/metrics`) | ✅ live |
| TanStack Query foundation | ✅ live |
| BSE corporate-announcement crawler | ⏳ deferred |
| Streaming chat (SSE) | ⏳ P2 |
| MCP server | ⏳ P2 |
| Auth0 / Clerk migration | ⏳ trigger: 1k MAU |

---

## How to use this folder

- **Building a feature?** Read `SHIPPED.md` to understand the current substrate, then `07_round2_broker_grade_plan.md` to see what's already on the roadmap. If your work is novel, add a new `08_*.md` plan and reference it from this index.
- **Onboarding?** Read `SHIPPED.md` → `ARCHITECTURE_OVERVIEW.md` → `/GETTING_STARTED.md`.
- **Reviewing a PR?** Verify the change updates `SHIPPED.md` if it adds endpoints, env vars, migrations, or subagents.
- **Re-architecting?** The Round 0 design docs (00–05) are the historical record — don't rewrite them, write a new plan instead.
