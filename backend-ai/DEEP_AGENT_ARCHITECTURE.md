# Deep Agent Architecture (Current)

Shape of the LangGraph agent system as deployed today. For the broader plan + roadmap, see [`/plans/SHIPPED.md`](../plans/SHIPPED.md) and [`/plans/07_round2_broker_grade_plan.md`](../plans/07_round2_broker_grade_plan.md). For coding rules, see [`/AGENTS.md`](../AGENTS.md).

## High-level flow

```
User /chat/query
    │
    ▼
ChatService           [src/domains/chat/service.py]  ─ JWT-gated, persists ChatSession + ChatMessage
    │
    ▼
Orchestrator (Minerva)   [src/agents/orchestrator.py]   ─ build_research_agent() via deepagents
    │ routing decisions per [src/agents/prompts/orchestrator.py]
    ▼
Specialist subagents  [src/agents/subagents/*]       ─ 11 of them, see below
    │
    ▼
Tool layer            [src/agents/tools/*]           ─ all math, DB reads, vector search, regex
    │
    ▼
Final synthesis      ─ structured Markdown skeleton enforced by [src/schemas/structured_analysis.py]
```

The orchestrator and every subagent are built with `deepagents>=0.4.12`, which wraps LangGraph. Memory + checkpointer config lives in [`src/agents/memory.py`](src/agents/memory.py).

## Subagents (11)

Declared in [`src/agents/subagents/__init__.py`](src/agents/subagents/__init__.py); each module exports a `get_<name>_subagent()` factory returning `{name, description, system_prompt, tools}`.

| Name | When the orchestrator dispatches to it | Source |
|---|---|---|
| `company-analysis` | Single company deep dive — financials, ratios, risk + governance flags, filings, news | [subagents/company.py](src/agents/subagents/company.py) |
| `comparison` | 2–5 companies side-by-side on growth / profitability / leverage / valuation / risk | [subagents/comparison.py](src/agents/subagents/comparison.py) |
| `discovery` | Hidden / asymmetric exposure (Castrol → Data Centres style) and 2-hop second-order effects | [subagents/discovery.py](src/agents/subagents/discovery.py) |
| `portfolio` | Holdings, concentration, sector allocation, news-for-top-holdings | [subagents/portfolio.py](src/agents/subagents/portfolio.py) |
| `news-sentiment` | Recent news + sentiment aggregation per company / sector | [subagents/news.py](src/agents/subagents/news.py) |
| `doc-insight` | User-uploaded PDFs / PPTs with page-level citations | [subagents/doc_insight.py](src/agents/subagents/doc_insight.py) |
| `policy-macro` | "Who benefits / suffers from policy X?" causal cross-industry analysis | [subagents/policy_macro.py](src/agents/subagents/policy_macro.py) |
| `theme-explorer` | Theme-first browsing — "show me companies most exposed to AI / EV / etc." | [subagents/theme_explorer.py](src/agents/subagents/theme_explorer.py) |
| `transcript-analyst` | Earnings call commentary, guidance, capex, supply-chain mentions | [subagents/transcript_analyst.py](src/agents/subagents/transcript_analyst.py) |
| `macro-commodity` | Macro / commodity / FX moves → Indian equity exposure | [subagents/macro_commodity.py](src/agents/subagents/macro_commodity.py) |
| `graph-reasoning` | Multi-hop relation-graph traversal (supplier-of-supplier, second-order policy impact) | [subagents/graph_reasoning.py](src/agents/subagents/graph_reasoning.py) |

Routing keywords are documented in [`src/agents/prompts/orchestrator.py`](src/agents/prompts/orchestrator.py). Trigger words like *hidden / asymmetric / non-obvious / second-order / ripple / who else benefits* fire `discovery`. The orchestrator may also invoke `discovery` in parallel with `company-analysis` for "thorough" or "deep" analysis requests.

## Discovery vertical (the asymmetric-insight engine)

This is the headline differentiator. Two parts:

**Offline, periodic** — [`src/agents/etl_agents/theme_agent.py`](src/agents/etl_agents/theme_agent.py) implements a **two-pass tagger**:

1. *Classify* — given a company × theme pair, the LLM returns `exposure_type, impact, impact_direction, impact_horizon, evidence_quotes (≥2), reasoning`. Confidence floor 0.55, evidence floor of 2 quotes (relaxed only for very strong keyword evidence).
2. *Asymmetric validator* — a second LLM pass judges whether the exposure is **non-obvious** given the company's primary sector / industry. The result lands in `company_themes.is_asymmetric`. Heuristic fallback marks `derivative` / `second_order` / `supplier` exposures with impact ≥0.4 as asymmetric.

Tags are upserted, stale ones deactivated, and a denormalised summary cached on `companies.thematic_exposure_summary`.

**Online, query-time** — the `discovery` subagent loads the precomputed tags and walks the theme graph:

- Tools: `get_company_themes`, `get_asymmetric_company_themes`, `search_themes`, `get_companies_in_theme`, `find_second_order_effects` (BFS over `theme → theme` edges with weight propagation, configurable depth), `find_supply_chain_links`, `get_macro_sensitivity`, plus the lower-level `get_relations` / `reverse_relations`.
- Prompt: [`src/agents/prompts/discovery.py`](src/agents/prompts/discovery.py). Lead with `is_asymmetric=true` rows; cite `evidence_quotes` verbatim; refuse to invent links.

API surface for the same data (consumed by the frontend Home view + Discovery feed):

- `GET /discovery/themes`, `/discovery/themes/{theme}/companies`, `/discovery/companies/{id}/themes`, `/discovery/asymmetric`, `/discovery/themes/{theme}/neighbors`. Source: [`src/domains/discovery/`](src/domains/discovery/).

## Structured output skeleton

Every analytical chat response follows this 14-section Markdown skeleton (sections may be skipped when the underlying tool returns nothing; required sections are bold):

1. **`## Business Overview`**
2. `## Domain & Subdomain Exposure`
3. `## Hidden / Asymmetric Exposure`
4. `## Growth Drivers`
5. `## Cost Drivers`
6. `## Financial Health`
7. `## Risk Flags`
8. `## Macro Sensitivity`
9. `## Second-Order Effects`
10. `## Valuation Commentary`
11. `## Bull vs Bear`
12. **`## Explained Simply`** (expertise-adapted)
13. `## Sources`
14. **`## Suggested follow-ups`** (exactly three)

Pydantic contract: [`src/schemas/structured_analysis.py`](src/schemas/structured_analysis.py). The `validate_markdown_skeleton()` helper performs a light regex sweep for required sections; missing required sections trigger a single retry with a sharper instruction.

## Tools

Catalogue: [`src/agents/tools/__init__.py`](src/agents/tools/__init__.py). Categories:

- **Financial** — `get_latest_financials`, `calculate_ratios`, `detect_risk_flags` (8 ratio thresholds), `detect_governance_flags` (regex over filing pages — promoter pledge, auditor change, related-party transactions, contingent liabilities, qualified opinion, default disclosure — plus a 3σ margin-anomaly check).
- **Vector** — `search_filings`, `search_news_semantic`, `search_transcripts`, `search_user_upload`, `search_social`.
- **Discovery / themes** — `get_company_themes`, `get_asymmetric_company_themes`, `search_themes`, `get_companies_in_theme`, `find_second_order_effects`, `find_supply_chain_links`, `get_macro_sensitivity`.
- **Relations / graph** — `get_relations`, `reverse_relations`, `traverse_graph`.
- **News / events / insights** — `get_recent_news`, `search_events`, `list_daily_insights`, `get_insight`.
- **Transcripts** — `get_transcript_segments`, `list_recent_transcripts`.
- **Portfolio** — `get_portfolio_holdings`, `calculate_portfolio_metrics`, `get_user_primary_portfolio`.
- **Macro / commodity** — `get_macro_series`, `get_commodity_series`, `commodity_exposure`.
- **Document / web** — `parse_pdf`, `parse_ppt`, `fetch_url`, `internet_search`, `resolve_company`.

Tools do all math, ratios, vector search, regex, and DB reads. LLMs only interpret.

## Memory model

[`src/agents/memory.py`](src/agents/memory.py) configures:

- **CompositeBackend** — routes `/memories/*` paths to a persistent `StoreBackend` (PostgresStore in prod, InMemoryStore in dev) and ephemeral state to a `StateBackend`.
- **MemorySaver** — checkpointer keyed by `thread_id = session_id` for within-session continuity.
- **Skill seeding** — pre-loads markdown bundles from [`src/agents/skills/`](src/agents/skills/) (`indian-equity-analysis`, `annual-report-analysis`, `portfolio-strategy`) into the store for progressive disclosure.

The orchestrator prompt instructs the agent to read / write three memory files:

- `/memories/user_preferences.txt` — expertise level, sectors of interest, analysis style.
- `/memories/watchlist.txt` — companies the user frequently asks about.
- `/memories/research_notes/<entity>.txt` — short summaries of past analyses for continuity.

## API entrypoint

`POST /chat/query` is the primary runtime path:

- [`src/domains/chat/routes.py`](src/domains/chat/routes.py) — request schema + JWT + `assert_self`.
- [`src/domains/chat/service.py`](src/domains/chat/service.py) — builds / reuses the orchestrator via `build_research_agent()`, persists messages to `chat_sessions` / `chat_messages`, retries `output_parse_failed` once.

Other agent-touching paths:

- `POST /chat/upload` — multipart document upload; populates `user_uploads` and indexes into Qdrant for `doc-insight`.
- `POST /compare/` — multi-company comparison driven by the `comparison` subagent.

## Offline ETL agents

These run on Celery workers, not at query time:

- `ThemeTaggingAgent` — described above. Task: `etl.tag_themes`.
- `EventExtractionAgent` — extracts material events from filings / news. Task: `etl.extract_events`.
- `InsightDiscoveryAgent` — produces daily Insight Engine cards. Task: `etl.compute_daily_insights`.
- `InsightRevalidationAgent` — periodically revalidates active insights. Task: `etl.revalidate_insights`.
- `SupplyChainAgent` + `PatternMiningAgent` — Phase-2 graph builders. Tasks: `etl.mine_supply_chain`, `etl.mine_patterns`, `etl.backfill_graph_edges`.

Other ETL hygiene:

- `etl.summarize_filing` (auto-fires after `etl.parse_filing`) — produces the AI one-liners for the Timeline, persisted to `filing_summaries`.
- `etl.evaluate_alert_rules` + `etl.deliver_alert_events` — alert evaluator + delivery.
- `etl.monitor_stuck_runs` — reaps `running` rows older than 2h.
- `etl.discover_new_listings` — auto-chains refresh for newly added companies.

All tasks are registered in [`src/etl/tasks.py`](src/etl/tasks.py). ETL run statuses are tracked in `etl_runs` and counted via `etl_run_status_total{pipeline,status}` in `/metrics`.

## Observability per agent invocation

[`src/observability.py`](src/observability.py) exposes:

- `record_agent_invocation(subagent, outcome)` — increments `agent_invocations_total`.
- `record_tool_call(tool)` — increments `tool_calls_total`.
- Cache hit/miss counters via `record_cache(...)`.
- `etl_run_status_total{pipeline, status}` — written by `_finish_etl_run`.
- `alerts_fired_total{condition_type}` — written by the alert evaluator.

Hook these when adding a new subagent or tool — don't introduce a parallel metrics layer.

## Where the design diverges from `/plans/04_langgraph_agent_design.md`

- We use the **`deepagents` wrapper** (LangGraph under the hood) instead of a hand-rolled `StateGraph`. This collapses router + specialist + synthesis nodes into a single `create_deep_agent` call with subagent definitions.
- We have **11 subagents**, not 5. The original plan listed `Router / CompanyAnalysis / Comparison / Portfolio / NewsSentiment / DocInsight / Synthesis`; we added `discovery / policy-macro / theme-explorer / transcript-analyst / macro-commodity / graph-reasoning` and dropped the explicit Router/Synthesis nodes (the orchestrator prompt handles both).
- The original plan didn't include the **two-pass asymmetric tagger**, the **structured-output Pydantic contract**, the **governance-flags tool**, or the **`/discovery/*` API surface** — all added in Round 1.
- Memory uses `deepagents`-native `CompositeBackend` + `MemorySaver`, not a custom Redis wrapper.

The original plan is retained for historical reference. **[`/plans/SHIPPED.md`](../plans/SHIPPED.md) is the source of truth for current state.**

## Notes

- The legacy `src/deep_research` package is gone.
- New subagents must register in [`src/agents/subagents/__init__.py`](src/agents/subagents/__init__.py) AND add a routing entry in [`src/agents/prompts/orchestrator.py`](src/agents/prompts/orchestrator.py).
- Update this file in the same PR as any change to the orchestration topology — drift is the worst kind of bug.
