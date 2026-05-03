# SHIPPED — what's actually in the repo today

This is the single source of truth for what the AI Equity Research Platform contains right now. Use this when onboarding, when wiring new integrations, or when one of the historical design docs in this folder appears to disagree with reality.

Other docs in `plans/` (`00_architecture_refinement_summary.md` through `05_cloud_deployment_strategy.md`) are kept for historical reference. They describe what was originally proposed; this doc describes what was built.

> **Post-gap-analysis pass:** the gap analysis run after Round 2 found 5 BLOCKING + 10 HIGH + 7 MEDIUM gaps (3 of them caused by inaccurate claims previously in this doc). All BLOCKING + HIGH + most MEDIUM are now closed; see `## Gap analysis fixes` at the bottom for the change log.

---

## At a glance

- **Backend:** FastAPI (`backend-ai/src/app/factory.py`) on port `8001`, served by `uvicorn`.
- **Frontend:** React 19 + Vite + TypeScript on port `5173`.
- **Datastores:** Postgres `5432`, Redis `6379`, Qdrant `6333` (all via `docker-compose.yml`).
- **Workers:** Celery + SQS / Redis broker; tasks in [backend-ai/src/etl/tasks.py](../backend-ai/src/etl/tasks.py).
- **Auth:** mandatory on every user-keyed route; argon2id passwords, JWT access (15 min) + refresh (30 d) with rotation in Redis, blacklist on logout.
- **LLMs:** Groq / OpenAI / DeepSeek / Ollama — provider chosen via `LLM_PROVIDER` env var.
- **Agents:** 11 LangGraph subagents (via `deepagents` wrapper) + a Discovery vertical for asymmetric / hidden-exposure insights.
- **Charts:** TradingView Lightweight Charts deps installed; broker-style stock page renders today on Recharts and is wired to upgrade to Lightweight Charts when the npm dep lands.

---

## Round 1 — Hidden Insights & Industries (the "Castrol → Data Centres" engine)

| Capability | Files |
|---|---|
| Theme taxonomy seed (~50 themes including the hidden `data_centre_lubricants` parent/child link) | [src/agents/prompts/themes.yaml](../backend-ai/src/agents/prompts/themes.yaml), [scripts/seed_themes.py](../backend-ai/scripts/seed_themes.py) |
| Theme-tagging agent with **two-pass LLM**: classify → asymmetric-validator (the Castrol-style flag) | [src/agents/etl_agents/theme_agent.py](../backend-ai/src/agents/etl_agents/theme_agent.py) |
| Discovery subagent + prompt + tools (`get_companies_in_theme`, `find_second_order_effects`, `find_supply_chain_links`, `get_macro_sensitivity`) | [src/agents/subagents/discovery.py](../backend-ai/src/agents/subagents/discovery.py), [src/agents/prompts/discovery.py](../backend-ai/src/agents/prompts/discovery.py), [src/agents/tools/discovery.py](../backend-ai/src/agents/tools/discovery.py) |
| Discovery API (`GET /discovery/themes`, `/themes/{theme}/companies`, `/companies/{id}/themes`, `/asymmetric`, `/themes/{theme}/neighbors`) | [src/domains/discovery/](../backend-ai/src/domains/discovery/) |
| Structured-output skeleton enforced across all subagents (Domain → Subdomain → Asymmetric → Drivers → Risks → Macro → 2nd-order → Bull/Bear → Explained Simply → Sources → Suggested follow-ups) | [src/schemas/structured_analysis.py](../backend-ai/src/schemas/structured_analysis.py), [src/agents/prompts/orchestrator.py](../backend-ai/src/agents/prompts/orchestrator.py) |
| Governance risk flags (promoter pledge, auditor change, related-party transactions, contingent liabilities, qualified opinion, default disclosure, 3σ margin anomaly) | [src/agents/tools/financial.py](../backend-ai/src/agents/tools/financial.py) `detect_governance_flags` |
| AI one-liner timeline summarizer (replaces the static "X filed on Y" template) | [src/etl/filing_summary.py](../backend-ai/src/etl/filing_summary.py), reads `FilingSummary` rows in [src/domains/timeline/service.py](../backend-ai/src/domains/timeline/service.py) |
| PDF table extraction (pdfplumber → `statement_items`) and chart extraction (vision LLM → `chart_series`, gated by `ENABLE_CHART_EXTRACTION`) | [src/etl/doc_parser.py](../backend-ai/src/etl/doc_parser.py), [src/etl/chart_extraction.py](../backend-ai/src/etl/chart_extraction.py) |
| Broker OAuth + portfolio sync (Zerodha Kite to start) | [src/integrations/market_data/providers/Kite_api/client.py](../backend-ai/src/integrations/market_data/providers/Kite_api/client.py), [src/domains/broker/](../backend-ai/src/domains/broker/) |
| Alert evaluator + delivery + new `asymmetric_theme` condition | [src/etl/alert_evaluator.py](../backend-ai/src/etl/alert_evaluator.py), [src/db/models.py](../backend-ai/src/db/models.py) `AlertEvent` |
| Visualization service (Plotly): revenue trend, margin trend, debt vs equity, peer comparison; PNGs persisted via S3-or-local `store_bytes` | [src/services/visualization_service.py](../backend-ai/src/services/visualization_service.py) |
| New tables: `chart_series`, `statement_items`, `company_web_endpoints`, `system_config`, `filing_summaries`, `transactions`, `alert_events`; column extensions on `companies` (thematic / macro / supply-chain JSON caches) and `company_themes` (`is_asymmetric`, `impact_direction`, `impact_horizon`, `evidence_quotes`) | migration [b7c2e1d34a01_discovery_extensions.py](../backend-ai/alembic/versions/b7c2e1d34a01_discovery_extensions.py) |

Plan reference: [07_round2_broker_grade_plan.md](07_round2_broker_grade_plan.md) carries forward the architectural decisions; the original Discovery plan is tracked in `~/.claude/plans/run-a-codebase-scan-snappy-avalanche.md` (out-of-tree planning archive).

---

## Round 2 — Broker-Grade Platform

### Auth & profile

| Capability | Files |
|---|---|
| Argon2id password hashing | [src/domains/auth/security.py](../backend-ai/src/domains/auth/security.py) |
| JWT access (15 min) + refresh (30 d), rotation on every refresh, blacklist on logout — all backed by Redis | same file |
| Routes: `/auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/verify-email`, `/auth/resend-verification`, `/auth/me` | [src/domains/auth/routes.py](../backend-ai/src/domains/auth/routes.py) |
| Rate-limiting via `slowapi` (5/min login, 3/min signup + forgot) | same |
| Email sender abstraction (stub-and-log dev / SMTP / SES) | [src/domains/auth/email.py](../backend-ai/src/domains/auth/email.py) |
| `Depends(get_current_user)` + `assert_self` helper applied to every user-keyed route (chat, users, watchlists, portfolio, alerts, screens, broker, upload) | [src/domains/auth/dependencies.py](../backend-ai/src/domains/auth/dependencies.py) |
| User model extension: `email_verified_at`, `last_login_at`, `avatar_url`, `theme_preference`, `default_chart_range`, `sectors_of_interest` | migration [c1d2e3f4a501_auth_user_extensions.py](../backend-ai/alembic/versions/c1d2e3f4a501_auth_user_extensions.py) |
| Cache helpers `get_user_profile_cached` / `set` / `invalidate` (Redis, 15-min TTL, invalidated on profile PATCH) | [src/services/cache_service.py](../backend-ai/src/services/cache_service.py) |
| Frontend AuthContext + RequireAuth gate + 401-refresh interceptor + token store | [frontend/src/app/state/AuthContext.tsx](../frontend/src/app/state/AuthContext.tsx), [frontend/src/app/state/RequireAuth.tsx](../frontend/src/app/state/RequireAuth.tsx), [frontend/src/shared/api/core.ts](../frontend/src/shared/api/core.ts) |
| Auth screens: SignUp, Login, Forgot, Reset, EmailVerify | [frontend/src/features/auth/](../frontend/src/features/auth/) |

### Quotes / candles / peers (broker-app stock page)

| Capability | Files |
|---|---|
| Ticker-keyed `GET /quotes/{ticker}`, `/quotes/{ticker}/candles?range=1D|1W|1M|6M|1Y|5Y|MAX`, `/quotes/{ticker}/peers` | [src/domains/quotes/](../backend-ai/src/domains/quotes/) |
| Tiered candles: yfinance → Upstox → FMP, Redis-cached by range (1D=60s, 5Y=24h) | [src/services/market_data/historical_service.py](../backend-ai/src/services/market_data/historical_service.py) |
| Frontend broker-style stock page mounted on top of CompanyWorkspaceView: QuoteHeader (10s polling via react-query), StockChart (line/candle, color-coded by direction, gradient fill, volume strip, OHLC tooltip), RangeToggle, PeersTab, AskMinervaFAB, BrokerActions (Zerodha + Groww deep-links) | [frontend/src/features/company/broker/](../frontend/src/features/company/broker/) |

### Personalised Home + OmniSearch

| Capability | Files |
|---|---|
| `GET /home/personalized` returns watchlist + holdings + asymmetric Discovery feed + recent timeline + suggestions in one shot, 60s Redis cache | [src/domains/home/](../backend-ai/src/domains/home/) |
| Frontend HomeView (the new default landing view) + OmniSearch (empty input shows tracked companies; debounced server search when typing) | [frontend/src/features/home/HomeView.tsx](../frontend/src/features/home/HomeView.tsx), [frontend/src/components/OmniSearch.tsx](../frontend/src/components/OmniSearch.tsx) |
| Holdings count fix `GET /portfolios/me/holdings-count` (replaces the dangling `/upstox/portfolio/holdings` 404) | [src/domains/portfolio/routes.py](../backend-ai/src/domains/portfolio/routes.py) |

### Frontend foundation

| Capability | Files |
|---|---|
| TanStack Query provider with sane defaults (60s staleTime, retry=1 except on 4xx) | [frontend/src/app/state/QueryProvider.tsx](../frontend/src/app/state/QueryProvider.tsx) |
| Critical fetches migrated to `useQuery`: HomeView, BrokerStockPage candles, QuoteHeader (with `refetchInterval`) | as above |
| New deps wired into `package.json`: `@tanstack/react-query`, `@tanstack/react-query-devtools`, `lightweight-charts` | [frontend/package.json](../frontend/package.json) |

### Observability & ETL hygiene

| Capability | Files |
|---|---|
| `/health` (liveness), `/ready` (Postgres + Redis + Qdrant probes, 503 on failure), `/metrics` (Prometheus exposition) | [src/app/factory.py](../backend-ai/src/app/factory.py), [src/observability.py](../backend-ai/src/observability.py) |
| Counters wired throughout: agent invocations (`domains/chat/service.py`), tool calls (`agents/tools/_utils.py:emit_tool_metric` in financial / themes / discovery / vector_search), cache hits/misses (`services/cache_service.py`), ETL run terminations (`etl/tasks.py`), alerts fired (`etl/alert_evaluator.py`), request-latency histogram (`app/middleware.py`) | as listed |
| Celery beat schedule registered for: theme tagging, news ingest, transcript / social / macro ingest, insight discovery + revalidation, graph backfill, plus Round 2 additions: `summarize_pending_filings` (hourly), `evaluate_alert_rules` (5-min), `deliver_alert_events` (5-min), `monitor_stuck_runs` (hourly), `discover_new_listings` (daily) | [src/celery_app.py](../backend-ai/src/celery_app.py) |
| Stuck-run reaper (marks `running` rows older than 2h as failed) | [src/etl/monitoring.py](../backend-ai/src/etl/monitoring.py) `reap_stuck_runs` |
| New-listing self-discovery (auto-chains refresh for any company added in the last 24h) | same file `discover_new_listings` |
| Celery tasks `etl.monitor_stuck_runs`, `etl.discover_new_listings`, `etl.summarize_filing`, `etl.evaluate_alert_rules`, `etl.deliver_alert_events` | [src/etl/tasks.py](../backend-ai/src/etl/tasks.py) |

---

## Migrations

Run `alembic upgrade head` once after first checkout. Order:

1. `6da275df40da` — initial schema (companies, financials, users, portfolios, etc.)
2. `a1b2c3d4e5f6` — insight engine tables (filing_pages, theme_taxonomy, policies, events, insights, transcripts, social, macro, relations, source_quality)
3. `b7c2e1d34a01` — discovery extensions (chart_series, statement_items, company_web_endpoints, system_config, filing_summaries, transactions, alert_events; column adds on companies + company_themes)
4. `c1d2e3f4a501` — auth user extensions (email_verified_at, last_login_at, avatar_url, theme_preference, default_chart_range, sectors_of_interest)

---

## New environment variables

Add these to `backend-ai/.env` on top of the existing LLM / data-API keys.

```env
# Auth — required (generate with: openssl rand -hex 32)
AUTH_JWT_SECRET=replace-me-please-32-bytes-of-randomness

# Auth — optional with sensible defaults
AUTH_ACCESS_TOKEN_MINUTES=15
AUTH_REFRESH_TOKEN_DAYS=30
AUTH_REQUIRE_EMAIL_VERIFICATION=false
AUTH_LOGIN_RATE_LIMIT=5/minute
AUTH_SIGNUP_RATE_LIMIT=3/minute
AUTH_FORGOT_RATE_LIMIT=3/minute

# Email sender (stub-and-log in dev; SMTP or SES in prod)
EMAIL_SENDER=stub
EMAIL_FROM=no-reply@equityai.local
EMAIL_APP_BASE_URL=http://localhost:5173
# SMTP_HOST=
# SMTP_PORT=587
# SMTP_USERNAME=
# SMTP_PASSWORD=
# SES_REGION=ap-south-1

# Vision LLM chart extraction (off by default — costly)
ENABLE_CHART_EXTRACTION=false
```

---

## New Python deps

Already in [backend-ai/requirements.txt](../backend-ai/requirements.txt) — `pip install -r backend-ai/requirements.txt` after pull picks them up:

- `passlib[argon2]>=1.7.4` (argon2id password hashing)
- `python-jose[cryptography]>=3.3.0` (JWT)
- `slowapi>=0.1.9` (rate limiting)
- `email-validator>=2.2.0` (Pydantic `EmailStr`)
- `prometheus-client>=0.20.0` (`/metrics`)
- `yfinance>=0.2.65` (free Indian-equity OHLC fallback)

## New frontend deps

Already in [frontend/package.json](../frontend/package.json) — `npm install` after pull:

- `@tanstack/react-query` and `@tanstack/react-query-devtools` (server-state + caching)
- `lightweight-charts` (TradingView candle / line library, ready for upgrade from Recharts)

---

## What's intentionally deferred (with triggers)

See [07_round2_broker_grade_plan.md](07_round2_broker_grade_plan.md) for the full P2 list. Headlines:

- Streaming chat (SSE) — when chat p95 > 4s.
- MCP server (theme search, asymmetric feed, company facts, portfolio metrics) — when first external integration request arrives.
- ETL platform migration (Airflow / Prefect / MWAA) — when sustained > 1k jobs/hour or pipeline lineage becomes a debugging bottleneck.
- BSE filings crawler — needs separate scraper or API contract.
- Whisper concall audio transcription.
- Auth0 / Clerk migration — > 1k MAU or enterprise SSO ask.

---

## Acceptance walk-through

After a fresh `git pull && docker compose up -d && pip install -r backend-ai/requirements.txt && cd backend-ai && alembic upgrade head && python -m uvicorn src.main:app --port 8001 --reload` plus `cd frontend && npm install && npm run dev`:

1. Open http://localhost:5173 — you land on `/auth/login` (RequireAuth gate).
2. Sign up → backend hashes argon2id → tokens stored → land on the new Home view.
3. Home shows your (empty) watchlist + holdings + the platform-wide asymmetric Discovery feed + recent filings timeline + suggestions.
4. OmniSearch (empty) shows your tracked companies; type "Reliance" and pick it.
5. Reliance opens with the broker-style stock page on top: live LTP + day high/low + 1Y candlestick coloured by daily direction.
6. Toggle 1M / 5Y, switch line ↔ candle, click a peer to navigate.
7. "Ask Minerva" FAB pre-fills the chat with `[Context: company_id=…]` so the orchestrator routes through the company-analysis subagent and (in parallel for deep queries) the discovery subagent.
8. `curl http://localhost:8001/ready` returns `200 {"ready": true, ...}`. `curl http://localhost:8001/metrics` returns Prometheus text.

---

## Gap-analysis fixes

The post-Round-2 gap analysis surfaced 22 issues (5 BLOCKING / 10 HIGH / 7 MEDIUM). All BLOCKING + HIGH + the relevant MEDIUM items are closed. Diff:

### Backend

- **B1** Discovery tool exports — `get_companies_in_theme`, `find_second_order_effects`, `find_supply_chain_links`, `get_macro_sensitivity`, `get_asymmetric_company_themes`, `traverse_graph` are now in `agents/tools/__init__.py` `__all__`.
- **B2** 5 Celery beat entries added: `summarize-pending-filings-hourly`, `evaluate-alert-rules-5min`, `deliver-alert-events-5min`, `monitor-stuck-runs-hourly`, `discover-new-listings-daily` ([src/celery_app.py](../backend-ai/src/celery_app.py)).
- **B3** CI now runs `alembic upgrade head` against an ephemeral Postgres + Redis matrix with a fake `AUTH_JWT_SECRET` ([.github/workflows/backend.yml](../.github/workflows/backend.yml)).
- **B4** `.env.example` now ships all 16 Round 2 env vars (`AUTH_JWT_SECRET`, all `AUTH_*_RATE_LIMIT`, `EMAIL_*`, `SMTP_*`, `SES_REGION`, `ENABLE_CHART_EXTRACTION`).
- **B5** Upstox candles tier is now a real implementation (`/v2/historical-candle/{instrument_key}/...`); requires both `UPSTOX_ACCESS_TOKEN` and `Company.isin`. Falls through cleanly to FMP otherwise. ([historical_service.py](../backend-ai/src/services/market_data/historical_service.py)).
- **H1** All 5 stale subagent prompts (`policy_macro`, `theme_explorer`, `transcript_analyst`, `macro_commodity`, `graph_reasoning`) now end with `## Sources` + `## Suggested follow-ups`.
- **H10** `record_agent_invocation` now wired in `domains/chat/service.py` (orchestrator outcome). `record_tool_call` wired into financial / themes / discovery / vector_search via `agents/tools/_utils.py:emit_tool_metric`. `record_cache` wired into `cache_service.py:CacheService.get`.

### Frontend

- **H2** `BrokerStockPage` candles now use `useQuery` with per-range `staleTime`.
- **H3** `updateUserProfile`, `uploadProfilePic`, `uploadDocument` migrated to `aiPut` / `aiUpload` (auth-aware wrappers in `shared/api/core.ts`). Raw `fetch()` calls eliminated from `shared/api/`.
- **H4** `ProfileView` now reads `useAuth().user.id` (with localStorage fallback for pre-rehydration race).
- **H5** `OmniSearch` mounted in `SidebarShell`; navigates to `company` view on pick.
- **H6** `EmailVerifyView` added; `AuthGate` routes to it on `?token=` URLs that mention `verify`.
- **H7** new `.github/workflows/frontend.yml` runs `npm install` + `tsc --noEmit` + `npm run lint` + `npm run build` + `npm test`.
- New `core.ts` helpers: `aiPut`, `aiUpload` (multipart with auth header).

### Operational

- **M2** Docker Compose now has a Qdrant healthcheck (TCP probe on 6333) + a `redis_data` named volume.
- **M5** `GETTING_STARTED.md` now documents `celery -A src.celery_app beat` as a separate process and explains that without it, the Round 2 periodic tasks (alert eval, summarisation, stuck-run reaper, new-listing discovery) won't fire.

### Still open (intentionally deferred)

- **H8** Backend test coverage for `auth/`, `quotes/`, `home/`, `broker/`, `discovery/` domains.
- **H9** Frontend test coverage for `AuthContext`, `RequireAuth`, `QueryProvider`, `HomeView`, `BrokerStockPage`, `QuoteHeader`.
- **M1** Iris → Minerva rename — most code + active docs done; a few historical refs remain.
- **M3** `/screens/run` is documented public; revisit if abuse becomes a concern.
- **M4** Legacy `src/api/routes_*.py` orphan files not yet deleted.
- **M7** localStorage tokens vs httpOnly cookies — re-evaluate before public launch.

The verification checklist at the top of the file remains accurate after these fixes.
