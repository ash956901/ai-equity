# AI Equity Research Platform

AI-native equity research for Indian retail investors (NSE / BSE). Combines a LangGraph multi-agent backend ("Minerva") with a broker-style frontend, autonomous data ingestion (filings + concalls + news + macro + social), and a Discovery engine that surfaces *hidden / asymmetric* thematic exposure (the Castrol → Data Centres style insight).

**For "what's actually built right now," start at [plans/SHIPPED.md](plans/SHIPPED.md).** This README is the elevator pitch + setup sketch; `GETTING_STARTED.md` is the full guide.

---

## Services

| Service | Port | Tech |
|---|---|---|
| **Frontend** | 5173 | React 19 / Vite / TypeScript / TanStack Query / Recharts (with TradingView Lightweight Charts dep ready) |
| **Backend** | 8001 | FastAPI / LangGraph (via DeepAgents) / SQLAlchemy / argon2id+JWT auth / Prometheus `/metrics` |
| **PostgreSQL** | 5432 | Companies, financials, themes (with `is_asymmetric`), portfolios, transactions, filings, alerts, users |
| **Redis** | 6379 | Caching, JWT blacklist, refresh-token allowlist, Celery broker |
| **Qdrant** | 6333 | Vector search over filings, transcripts, news, social, user uploads |

Infra is `docker compose up -d`. App processes (uvicorn + Celery worker + Vite dev server) run on the host.

## Quick start

```bash
docker compose up -d                                       # Postgres / Redis / Qdrant

python3 -m venv backend-ai/.venv
source backend-ai/.venv/bin/activate
pip install -r backend-ai/requirements.txt                 # incl. passlib[argon2], jose, slowapi, prometheus-client, yfinance

cp backend-ai/.env.example backend-ai/.env                 # edit: set LLM key + AUTH_JWT_SECRET
cd backend-ai && alembic upgrade head                      # 4 migrations, idempotent
python scripts/seed_db.py                                  # seed companies/ratios/news (no test user — sign up via UI)
python -m uvicorn src.main:app --port 8001 --reload &

cd ../frontend && npm install && npm run dev               # http://localhost:5173
```

Open http://localhost:5173 → Sign up → land on the personalised Home view.

## Features

**Minerva chat** — multi-agent research assistant. 11 specialist subagents under one orchestrator (`company-analysis`, `comparison`, **`discovery`**, `portfolio`, `news-sentiment`, `doc-insight`, `policy-macro`, `theme-explorer`, `transcript-analyst`, `macro-commodity`, `graph-reasoning`). Every response follows a structured skeleton: Domain → Asymmetric Exposure → Drivers → Risk Flags → Macro → 2nd-Order Effects → Bull vs Bear → Explained Simply → Sources → 3 Suggested Follow-ups.

**Discovery** — surfaces *non-obvious* thematic exposure (e.g. Castrol India tagged to Data Centres via specialty coolants). Backed by an offline two-pass theme tagger (classify → asymmetric-validator) and a relation-graph walker for second-order ripples. APIs: `GET /discovery/asymmetric`, `/discovery/themes/{theme}/companies`, `/discovery/companies/{id}/themes`.

**Personalised Home** — first thing you see after login: your watchlist, your holdings, the platform-wide asymmetric Discovery feed, recent AI-summarised filings, plus sector-tuned suggestions. Single endpoint, 60s cache.

**Broker-style stock page** — click any company and see live LTP polling every 10s, OHLC strip, candle/line chart with 1D/1W/1M/6M/1Y/5Y/MAX toggles colour-coded by daily direction, volume strip, peer grid, and an *Ask Minerva* FAB that pre-fills the chat with `[Context: company_id=…]`. Tiered chart data: yfinance → Upstox → FMP.

**Portfolio** — manual entry and Zerodha Kite OAuth + holdings sync (`POST /broker/portfolios/{id}/sync`). Concentration / sector / red-flag analytics. Idempotent transaction log.

**Timeline** — AI-summarised one-liner per filing (replaces the "X filed on Y" template), with materiality / sentiment / event-type tags.

**Discovery / Minerva-aware screening** — screens can filter by theme codes, asymmetric-only, P/E, ROE, debt/equity (in addition to the legacy sector / market-cap filters).

**Alerts** — rules persisted; Celery evaluator fires `alert_events` rows on price thresholds, sentiment shifts, new filings, and *new asymmetric theme detected*.

**Document upload** — PDF/PPT into per-user Qdrant namespace; doc-insight subagent answers with page-level citations.

**Auth & profile** — argon2id passwords, JWT access + refresh with rotation in Redis, blacklist on logout, signup / login / forgot / reset / verify-email, rate-limited (5 login/min, 3 signup+forgot/min). Redis-cached user profile.

**Observability** — `/health` (liveness), `/ready` (Postgres + Redis + Qdrant probes), `/metrics` (Prometheus). Counters wired into agents, tools, cache, ETL, alerts, request middleware.

**Autonomous ETL** — Celery + scheduled tasks: NSE filing crawl, IR site auto-discovery, news + social ingestion, transcript ingestion, FinBERT sentiment, theme tagging, filing summarisation, macro/commodity sync, stuck-run reaper, new-listing self-discovery.

## Documentation

- **[plans/SHIPPED.md](plans/SHIPPED.md)** — single source of truth for what exists today, with file-path evidence.
- **[GETTING_STARTED.md](GETTING_STARTED.md)** — full setup, env vars, API reference, troubleshooting.
- **[plans/ARCHITECTURE_OVERVIEW.md](plans/ARCHITECTURE_OVERVIEW.md)** — current architecture diagram + decisions.
- **[plans/07_round2_broker_grade_plan.md](plans/07_round2_broker_grade_plan.md)** — Round 2 plan + locked decisions + P2 deferred-list with triggers.
- **[backend-ai/DEEP_AGENT_ARCHITECTURE.md](backend-ai/DEEP_AGENT_ARCHITECTURE.md)** — orchestrator + 11 subagents + tool layer + structured-output contract.
- **[AGENTS.md](AGENTS.md)** — coding conventions for AI agents (and humans) working on the repo.
- **plans/00–05** — historical design docs. Each carries a "Status (as of Round 2)" banner; consult `SHIPPED.md` when in doubt.

## Tech stack

- **LLMs:** Groq / OpenAI / DeepSeek / Ollama (configurable via `LLM_PROVIDER`).
- **Embeddings:** Ollama `nomic-embed-text` (default) or OpenAI `text-embedding-3-small`.
- **Agents:** LangGraph via `deepagents>=0.4.12` wrapper. Sentry-style observability counters in `src/observability.py`.
- **DB:** PostgreSQL 15 with SQLAlchemy 2.x. Alembic migrations are idempotent (re-runnable on `Base.metadata.create_all` databases).
- **Vector:** Qdrant; 5 collections (`company_filings`, `news_articles`, `transcripts`, `social_posts`, `user_uploads`).
- **Auth:** `passlib[argon2]` + `python-jose`. Refresh rotation + blacklist in Redis.
- **Charts:** Recharts today; `lightweight-charts` is installed and ready for upgrade.
- **Data APIs:** FMP, FRED, NewsAPI, NewsData.io, yfinance (Indian equities EOD/intraday), Upstox, Kite Connect.
- **Workers:** Celery; queues per pipeline (`crawlers`, `parsers`, `embeddings`, `news`, `theme_tagging`, `alert_eval`).
- **Infra:** Docker Compose locally; AWS-ready (ECS/RDS/SQS/EventBridge per `plans/05_cloud_deployment_strategy.md`).

## Repository layout (top level)

```
ai-equity/
├── backend-ai/              # FastAPI + LangGraph backend (port 8001)
├── frontend/                # React 19 + Vite SPA (port 5173)
├── plans/                   # Design docs + SHIPPED.md (current state)
├── docker-compose.yml       # Postgres + Redis + Qdrant
└── README.md / GETTING_STARTED.md / AGENTS.md
```
