# AI Equity Research Platform — Architecture Overview

**Backend + frontend, agent-centric, broker-grade, for Indian equities (NSE / BSE)**

For "what's actually built today," with file-path evidence, see [SHIPPED.md](./SHIPPED.md). For the active phased plan, see [07_round2_broker_grade_plan.md](./07_round2_broker_grade_plan.md).

---

## System diagram

```
                                    +----------------------+
                                    |  Frontend (React 19) |
                                    |        :5173         |
                                    |  AuthContext +       |
                                    |  RequireAuth +       |
                                    |  TanStack Query      |
                                    +----------+-----------+
                                               |  REST + JWT (Bearer)
                                               v
                  +----------------------------+----------------------------+
                  |                  FastAPI backend (:8001)                |
                  |  argon2id + JWT (access 15m / refresh 30d, rotation)    |
                  |                                                         |
                  |   Public:                Authenticated:                 |
                  |   /auth/*                /chat/* /portfolios/*          |
                  |   /quotes/*              /watchlists/* /alerts/*        |
                  |   /discovery/*           /screens/* /broker/*           |
                  |   /timeline/             /home/personalized             |
                  |   /companies/* (read)    /chat/upload                   |
                  |   /health /ready /metrics                               |
                  +----+----+----+----+--------+--------+--------+----------+
                       |    |    |    |        |        |        |
        +--------------v--+ |    |    |        |        |        |
        | LangGraph (Minerva)| |    |    |        |        |        |
        | 11 subagents    | |    |    |        |        |        |
        | structured-out  | |    |    |        |        |        |
        +--------+--------+ |    |    |        |        |        |
                 |          |    |    |        |        |        |
                 v          |    |    |        |        |        |
            Tool layer  ----+    |    |        |        |        |
            (17+ tools)          |    |        |        |        |
                                 v    v        v        v        v
                          +------+----+----+---+--+----+--+----+--+
                          |  PostgreSQL  | Redis | Qdrant | S3  |
                          |    :5432     | :6379 | :6333  |     |
                          | 30+ tables   | cache | 5 col  | docs|
                          | + alerts     | jwt   |        |     |
                          +------+-------+-------+--------+-----+
                                 ^
                                 |
                          Celery workers (offline)
                          - NSE filing crawl (BSE: deferred)
                          - IR site auto-discovery
                          - News + social ingestion + FinBERT
                          - Transcript ingestion
                          - Theme tagging (two-pass: classify + asymmetric)
                          - Filing one-liner summarisation
                          - Macro / commodity sync
                          - Alert evaluator + delivery
                          - Stuck-run reaper + new-listing self-discovery
```

---

## Technology stack

- **Frontend:** React 19 / TypeScript / Vite / TanStack Query / Recharts (with `lightweight-charts` ready). Hand-rolled CSS variables in `frontend/src/index.css`. No Tailwind, no `assistant-ui`.
- **Backend:** Python 3.11 / FastAPI / LangGraph (via `deepagents>=0.4.12`) / SQLAlchemy 2.x / Pydantic v2.
- **Auth:** `passlib[argon2]` + `python-jose` + `slowapi` rate limiting. Refresh-rotation + JWT blacklist live in Redis.
- **LLMs:** Groq / OpenAI / DeepSeek / Ollama, configurable via `LLM_PROVIDER`.
- **Embeddings:** Ollama `nomic-embed-text` (768d default) or OpenAI `text-embedding-3-small` (1536d).
- **Databases:** PostgreSQL 15 (relational) + Qdrant (vector, 5 collections) + Redis (cache + Celery broker). S3 (or local fallback) for raw docs and chart PNGs.
- **Workers:** Celery; queues per pipeline.
- **Observability:** structlog + request-id middleware; Prometheus counters via `prometheus-client`; `/health`, `/ready`, `/metrics`.
- **DevOps:** Docker Compose locally; AWS-ready (ECS / RDS / SQS / EventBridge).

---

## Subagents (11)

The orchestrator dispatches to one or more of these per query. Routing keywords are documented in `src/agents/prompts/orchestrator.py`.

| Subagent | When it fires |
|---|---|
| `company-analysis` | Single-company deep-dive: financials, ratios, risk + governance flags, filings, news |
| `comparison` | 2–5 companies side-by-side on growth / profitability / leverage / valuation / risk |
| **`discovery`** | **Hidden / asymmetric exposure (Castrol → Data Centres style) + 2-hop second-order effects** |
| `portfolio` | Holdings, concentration, sector allocation, news for top holdings |
| `news-sentiment` | Recent news + sentiment aggregation per company / sector |
| `doc-insight` | User-uploaded PDFs / PPTs with page-level citations |
| `policy-macro` | "Who benefits / suffers from policy X?" causal cross-industry analysis |
| `theme-explorer` | Theme-first browsing — "show me companies most exposed to AI / EV / etc." |
| `transcript-analyst` | Earnings call commentary, guidance, capex, supply-chain mentions |
| `macro-commodity` | Macro / commodity / FX moves → Indian equity exposure |
| `graph-reasoning` | Multi-hop relation-graph traversal (supplier-of-supplier, second-order policy impact) |

Every analytical response follows the platform-wide structured-output skeleton (Pydantic contract: `src/schemas/structured_analysis.py`):

```
## Business Overview            (required)
## Domain & Subdomain Exposure
## Hidden / Asymmetric Exposure
## Growth Drivers / Cost Drivers
## Financial Health
## Risk Flags
## Macro Sensitivity
## Second-Order Effects
## Valuation Commentary
## Bull vs Bear
## Explained Simply             (required, expertise-adapted)
## Sources
## Suggested follow-ups         (required, exactly 3)
```

For details, see `/backend-ai/DEEP_AGENT_ARCHITECTURE.md`.

---

## Domain layout (current API surface)

| Domain | Purpose | Source |
|---|---|---|
| `auth` | signup / login / refresh / logout / forgot / reset / verify-email / `/auth/me` | `backend-ai/src/domains/auth/` |
| `home` | `GET /home/personalized` (60s cache) | `backend-ai/src/domains/home/` |
| `quotes` | `GET /quotes/{ticker}`, `/quotes/{ticker}/candles`, `/quotes/{ticker}/peers` | `backend-ai/src/domains/quotes/` |
| `discovery` | `/discovery/themes`, `/discovery/asymmetric`, theme→companies, company→themes | `backend-ai/src/domains/discovery/` |
| `broker` | Zerodha Kite OAuth flow + holdings sync | `backend-ai/src/domains/broker/` |
| `chat` | `POST /chat/query` + sessions + uploads | `backend-ai/src/domains/chat/` |
| `companies` | `/companies/`, `/companies/search`, `/companies/{id}/financials|ratios|quote|refresh` | `backend-ai/src/domains/companies/` |
| `portfolio` | CRUD + `/portfolios/me/holdings-count` | `backend-ai/src/domains/portfolio/` |
| `compare` | Multi-company analysis | `backend-ai/src/domains/compare/` |
| `alerts` | Rule CRUD; new `asymmetric_theme` condition | `backend-ai/src/domains/alerts/` |
| `watchlists` | Watchlist CRUD | `backend-ai/src/domains/watchlists/` |
| `screens` | `POST /screens/run` with theme + ratio filters | `backend-ai/src/domains/screens/` |
| `timeline` | `GET /timeline/?company_id=&days=` (AI one-liners) | `backend-ai/src/domains/timeline/` |
| `news` | `GET /get-news?query=&limit=` | `backend-ai/src/domains/news/` |
| `users` | `/users/{user_id}` profile + KYC | `backend-ai/src/domains/users/` |
| `insights` | Pre-computed Insight Engine cards | `backend-ai/src/domains/insights/` |

Health: `/health`, `/ready`, `/metrics`.

---

## Database (PostgreSQL)

30+ tables. Key clusters:

- **Companies & securities:** companies, exchanges, securities, indices.
- **Financials:** financial_statements_raw, financial_ratios, statement_items, chart_series.
- **Filings & content:** filings, filing_pages, filing_summaries (AI one-liners), transcripts, transcript_segments, news_articles, social_posts.
- **Discovery:** theme_taxonomy, company_themes (with `is_asymmetric`, `impact_direction`, `impact_horizon`, `evidence_quotes`), relation_edges, sector_commodity_links, macro_series, commodity_series.
- **Portfolio:** users (with `email_verified_at`, `last_login_at`, `theme_preference`, `default_chart_range`, `sectors_of_interest`), portfolios, holdings, transactions.
- **Insight engine:** events, policies, insights, insight_evidence, insight_outcomes, source_quality.
- **Operational:** alert_rules, alert_events, watchlists, watchlist_companies, saved_screens, chat_sessions, chat_messages, user_uploads, etl_runs, system_config.

Migrations are idempotent (`alembic upgrade head` is safe on existing DBs):
1. `6da275df40da` — initial schema
2. `a1b2c3d4e5f6` — insight engine tables
3. `b7c2e1d34a01` — discovery extensions
4. `c1d2e3f4a501` — auth user extensions

---

## Vector store (Qdrant)

5 collections, each carrying full metadata on every chunk:

- `company_filings` — parsed text from filings, presentations, concalls.
- `news_articles` — news + sentiment / impact / dimension metadata.
- `transcripts` — concall segments with speaker role + period.
- `social_posts` — Reddit / X / StockTwits posts with topic clusters.
- `user_uploads` — per-user namespace for ad-hoc document analysis.

Chunking via `_chunk_text` in `services/vector_service.py` (512-token windows, 64-token overlap). Embeddings via Ollama or OpenAI per env config.

---

## Discovery vertical (the headline differentiator)

Two parts working together:

**Offline (Celery)** — the two-pass theme tagger in `src/agents/etl_agents/theme_agent.py`:
1. *Classifier* LLM pass returns `exposure_type, impact, impact_direction, impact_horizon, evidence_quotes (≥2), reasoning`. Confidence ≥ 0.55 floor.
2. *Asymmetric validator* LLM pass judges whether the exposure is non-obvious from the company's primary sector. The result lands in `company_themes.is_asymmetric` — that's what powers the Castrol-style surfacing.

Stale tags are deactivated on each run; a denormalised summary lands on `companies.thematic_exposure_summary`. Theme→theme edges in `relation_edges` (seeded by `scripts/seed_themes.py`) drive the `find_second_order_effects` graph walk.

**Online (chat)** — the `discovery` subagent (`src/agents/subagents/discovery.py`) reads the precomputed tags and walks the graph at query time. Tools: `get_company_themes`, `get_asymmetric_company_themes`, `get_companies_in_theme`, `find_second_order_effects`, `find_supply_chain_links`, `get_macro_sensitivity`, `get_relations`, `reverse_relations`. Lead-with-asymmetric prompt; cite evidence quotes verbatim.

API surface: `GET /discovery/themes`, `/discovery/themes/{theme}/companies`, `/discovery/companies/{id}/themes`, `/discovery/asymmetric`, `/discovery/themes/{theme}/neighbors`. Discovery feed is the asymmetric-only stream surfaced on the frontend Home view.

---

## Frontend layout

```
src/
├── main.tsx                 # AuthProvider + RequireAuth + QueryProvider wrap
├── App.tsx                  # default view = "home"
├── app/
│   ├── components/          # AppContentRouter, SidebarShell
│   ├── state/               # AuthContext, RequireAuth, QueryProvider
│   ├── hooks/, constants.ts, types.ts
├── features/
│   ├── auth/                # SignUp, Login, Forgot, Reset, AuthGate
│   ├── home/HomeView.tsx    # default landing surface
│   ├── company/
│   │   ├── CompanyWorkspaceView.tsx     (legacy)
│   │   └── broker/                       (Round 2 broker-style stock page)
│   │       ├── BrokerStockPage.tsx
│   │       ├── StockChart.tsx           # candle/line, color-coded direction
│   │       ├── QuoteHeader.tsx          # 10s polling via react-query
│   │       ├── RangeToggle.tsx          # 1D/1W/1M/6M/1Y/5Y/MAX
│   │       ├── PeersTab.tsx
│   │       ├── BrokerActions.tsx        # Zerodha + Groww deep-links
│   │       └── AskMinervaFAB.tsx
│   ├── chat/, compare/, dashboard/, discovery/, filings/, news/,
│   ├── portfolio/, profile/, settings/, timeline/
├── components/OmniSearch.tsx           # default = your tracked companies
├── shared/api/                          # core (auth interceptor) + auth + home + quotes + ...
├── lib/api.ts                           # legacy compatibility surface
└── index.css                            # CSS variables
```

---

## Locked architectural decisions

(See `07_round2_broker_grade_plan.md` for the full table with rationale and reconsider triggers.)

| # | Decision | Choice |
|---|---|---|
| D1 | ETL orchestrator | Stay on Celery + SQS + Redis (OSS, free) |
| D2 | Auth | argon2id + JWT (15 min access / 30 d refresh, rotation in Redis) |
| D3 | Stock chart data | yfinance → Upstox → FMP, aggressively cached |
| D4 | Charting library | TradingView Lightweight Charts (Apache 2.0); Recharts in production today |
| D5 | Real-time price | 10s polling; SSE in P2 |
| D6 | Frontend server-state | TanStack Query |
| D7 | Chat streaming | Deferred to P2 |
| D8 | MCP exposure | Deferred to P2 |
| D9 | Deployment | Docker Compose locally; AWS-ready (ECS/RDS/SQS/EventBridge) |
| D10 | New SaaS spend ceiling P1 | ~$50/month |
| D11 | Async / parallel tools | Light: `asyncio.gather` for independent reads inside subagents |

---

## Non-functional targets

- p95 `/quotes/{ticker}` < 250 ms cold / < 30 ms warm.
- p95 `/quotes/{ticker}/candles` < 600 ms cold / < 80 ms warm.
- p95 `/discovery/asymmetric` < 200 ms warm.
- p95 chat-query end-to-end < 3 s (P1 polling); first-token < 500 ms after SSE in P2.
- Frontend cold-start TTI for `/company/{id}` < 1.5 s on 4G.
- Auth: argon2id (OWASP min cost params), HTTPS-only in prod, rate-limit 5 login + 3 signup/forgot per IP/min, refresh-token rotation, JWT blacklist on logout.
- Every API response carries `X-Request-ID`; ETL runs are tracked in `etl_runs` and `etl_run_status_total{pipeline,status}`.

---

## Cost estimate (MVP scale, ~hundreds of users)

~$400–500/month all-in:

- ECS Fargate (API + workers): $90
- RDS PostgreSQL: $80
- ElastiCache Redis: $50
- Qdrant on EC2: $70
- S3 + transfer: $25
- SQS + CloudWatch: $25
- LLM API: $50–150

P1 ceiling for *new* SaaS spend: ~$50/month (no managed orchestrator yet; Auth0/Clerk deferred).

---

## What's intentionally deferred (with triggers)

See `07_round2_broker_grade_plan.md` for the full P2 list. Headlines:

- Streaming chat (SSE) — when chat p95 > 4s.
- MCP server — when first external integration request arrives.
- ETL platform migration (Airflow / Prefect / MWAA) — when sustained > 1k jobs/hour.
- BSE filings crawler — needs a dedicated scraper or API contract.
- Whisper concall audio transcription.
- Auth0 / Clerk migration — > 1k MAU or enterprise SSO ask.

---

## Onboarding path

1. Read [SHIPPED.md](./SHIPPED.md) for what exists today.
2. Read this file for the architecture snapshot.
3. Read [`/GETTING_STARTED.md`](../GETTING_STARTED.md) and run the Quick Start.
4. Read [`/AGENTS.md`](../AGENTS.md) for the coding rules.
5. Pick a workstream from [07_round2_broker_grade_plan.md](./07_round2_broker_grade_plan.md) or the P2 deferred-list and add to it.
