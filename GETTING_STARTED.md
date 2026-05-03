# AI Equity Research Platform — Getting Started

End-to-end setup for running the full stack locally: infrastructure → backend → frontend → first signed-in chat query.

For "what's actually built today" with file-path evidence, see [plans/SHIPPED.md](plans/SHIPPED.md). For the architectural decisions behind the current state, see [plans/07_round2_broker_grade_plan.md](plans/07_round2_broker_grade_plan.md).

---

## Table of contents

1. [Architecture overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Quick start (5 minutes)](#3-quick-start-5-minutes)
4. [Detailed setup](#4-detailed-setup)
5. [Verifying the setup](#5-verifying-the-setup)
6. [Feature guide](#6-feature-guide)
7. [API reference](#7-api-reference)
8. [LLM configuration](#8-llm-configuration)
9. [Database management](#9-database-management)
10. [Troubleshooting](#10-troubleshooting)
11. [Project structure](#11-project-structure)

---

## 1. Architecture overview

Two app processes (FastAPI + Vite) and three datastores (Postgres + Redis + Qdrant). One Celery worker if you want the ETL pipelines running.

```
                       +-------------------+
                       |  Frontend (React) |
                       |   :5173           |
                       +---------+---------+
                                 | REST + JWT
                                 v
                       +-------------------+
                       |  FastAPI backend  |
                       |   :8001           |
                       |  /auth /quotes    |
                       |  /home /chat      |
                       |  /discovery       |
                       |  /broker /metrics |
                       +---+-----+-----+---+
                           |     |     |
                +----------v-+ +-v---+ +v-----+
                | PostgreSQL | |Redis| |Qdrant|
                |   :5432    | |:6379| |:6333 |
                +------------+ +-----+ +------+
```

The 11 LangGraph subagents (Minerva) live inside the FastAPI process; tool calls into the DB / Qdrant / external APIs happen in-process. Heavy ingestion (filing crawl, theme tagging, sentiment, summarisation) runs on Celery workers reading from the same Postgres / Redis / Qdrant.

---

## 2. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Docker + Compose | 20+ | `docker --version` |
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

**At least one LLM provider key:**

| Provider | Cost | How |
|---|---|---|
| Groq | Free tier | https://console.groq.com/keys |
| Ollama | Free / local | `brew install ollama` then `ollama pull deepseek-r1:8b nomic-embed-text` |
| OpenAI | Paid | Standard API key |
| DeepSeek | Paid | DeepSeek API key |

**Optional data API keys (graceful fallbacks if missing):** FMP, FRED, NewsAPI, NewsData.io, Upstox, Kite Connect.

---

## 3. Quick start (5 minutes)

```bash
cd ai-equity

# 1. Infrastructure
docker compose up -d

# 2. Backend deps + env
python3 -m venv backend-ai/.venv
source backend-ai/.venv/bin/activate
pip install -r backend-ai/requirements.txt

cp backend-ai/.env.example backend-ai/.env
# REQUIRED edits in backend-ai/.env:
#   LLM_PROVIDER=groq           (or ollama / openai / deepseek)
#   GROQ_API_KEY=gsk_...        (whichever provider you picked)
#   AUTH_JWT_SECRET=$(openssl rand -hex 32)
#   EMAIL_SENDER=stub           (dev: emails are logged, not sent)
#   EMAIL_APP_BASE_URL=http://localhost:5173

# 3. Database
cd backend-ai
alembic upgrade head           # 4 idempotent migrations
python scripts/seed_db.py      # 20 companies + ratios + news (no test user — sign up via UI)

# 4. Backend
python -m uvicorn src.main:app --port 8001 --reload &

# 5. Frontend
cd ../frontend
npm install                    # incl. @tanstack/react-query, lightweight-charts
npm run dev
```

Open http://localhost:5173 → you land on the login screen → click *Create account* → sign up → you land on the personalised Home view.

---

## 4. Detailed setup

### Step 1 — Infrastructure (Docker)

```bash
docker compose up -d
docker compose ps     # all three containers should be Up
```

Sanity:
```bash
docker exec ai-equity-postgres-1 pg_isready -U postgres
docker exec ai-equity-redis-1 redis-cli ping
curl http://localhost:6333/healthz
```

Stop without losing data: `docker compose down`. Wipe all data: `docker compose down -v`.

### Step 2 — Environment configuration

Copy and edit:

```bash
cp backend-ai/.env.example backend-ai/.env
```

#### Required (everything below)

```env
# Pick one LLM provider
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key
GROQ_MODEL=openai/gpt-oss-20b

# Auth — generate a real secret in prod (openssl rand -hex 32)
AUTH_JWT_SECRET=dev-only-change-me-in-production

# Email sender — stub logs reset / verify links to stdout in dev
EMAIL_SENDER=stub
EMAIL_FROM=no-reply@equityai.local
EMAIL_APP_BASE_URL=http://localhost:5173
```

#### Optional auth tunables (defaults shown)

```env
AUTH_ACCESS_TOKEN_MINUTES=15
AUTH_REFRESH_TOKEN_DAYS=30
AUTH_REQUIRE_EMAIL_VERIFICATION=false       # true = block login until verify-email is consumed
AUTH_LOGIN_RATE_LIMIT=5/minute
AUTH_SIGNUP_RATE_LIMIT=3/minute
AUTH_FORGOT_RATE_LIMIT=3/minute
```

#### Optional embeddings + vision + data APIs

```env
EMBEDDING_PROVIDER=ollama        # or openai
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768                # 1536 for OpenAI

ENABLE_CHART_EXTRACTION=false    # enables vision-LLM chart→JSON in doc_parser

FMP_API_KEY=...
FRED_API_KEY=...
NEWS_API_KEY=...
NEWSDATA_API_KEY=...
UPSTOX_API_KEY=...
UPSTOX_ACCESS_TOKEN=...
KITE_API_KEY=...
KITE_API_SECRET=...
```

### Step 3 — Backend

```bash
source backend-ai/.venv/bin/activate
pip install -r backend-ai/requirements.txt    # picks up new deps automatically
cd backend-ai
alembic upgrade head                          # idempotent; safe on existing DBs
python -m uvicorn src.main:app --port 8001 --reload
```

`alembic upgrade head` applies four migrations: `6da275df40da` (initial), `a1b2c3d4e5f6` (insight engine), `b7c2e1d34a01` (discovery extensions), `c1d2e3f4a501` (auth user extensions).

Verify:
```bash
curl http://localhost:8001/health     # {"status":"healthy"}
curl http://localhost:8001/ready      # {"ready":true,"postgres":{"ok":true},...}
curl http://localhost:8001/metrics    # Prometheus exposition
open http://localhost:8001/docs       # Swagger
```

### Step 4 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Optionally point at a non-default backend:
```env
# frontend/.env
VITE_BACKEND_URL=http://localhost:8001
```

Production build: `npm run build` then `npm run preview`.

### Step 5 — Database seeding

```bash
source backend-ai/.venv/bin/activate
python backend-ai/scripts/seed_db.py
python backend-ai/scripts/seed_themes.py    # taxonomy + theme→theme relation edges
```

The seed creates 20 Indian companies, financial ratios for the top 5, ~17 sample themes, sample news. **No test user is created** — sign up via the UI; auth is mandatory now.

To populate the asymmetric Discovery feed, run the theme tagger after some filings/news/transcripts have been ingested:

```bash
celery -A src.celery_app call etl.tag_themes  # via Celery beat / by hand
# or directly:
python -c "from src.agents.etl_agents.theme_agent import ThemeTaggingAgent; print(ThemeTaggingAgent().tag_universe(limit=50))"
```

Optional: start a Celery worker for the full ingestion pipeline:
```bash
# Worker — executes queued tasks
celery -A src.celery_app worker --loglevel=info -Q crawlers,parsers,embeddings,news,default

# Beat scheduler — fires the periodic tasks defined in src/celery_app.py
# (theme tagging, news ingest, alert evaluation, stuck-run reaper, etc.)
celery -A src.celery_app beat --loglevel=info
```

Run worker and beat as separate processes. In production they're typically
two ECS services / two systemd units. Without **beat**, none of the
periodic ETL tasks (alert evaluation, filing summarisation, theme tagging,
stuck-run reaper, new-listing self-discovery) will fire — they'd only run
on manual `.delay()` calls.

---

## 5. Verifying the setup

```bash
# 1. Infra
docker compose ps                                       # all Up

# 2. Backend
curl -s http://localhost:8001/ready | jq               # ready=true

# 3. Auth — sign up a test user
curl -s -X POST http://localhost:8001/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123","full_name":"Test User"}' \
  | jq

# Capture the access token from the response, then:
TOKEN="paste-access-token-here"

# 4. Personalised home
curl -s http://localhost:8001/home/personalized -H "Authorization: Bearer $TOKEN" | jq '.user'

# 5. Quote
curl -s http://localhost:8001/quotes/RELIANCE | jq

# 6. Candles
curl -s "http://localhost:8001/quotes/RELIANCE/candles?range=1Y" | jq '.ohlcv | length'

# 7. Asymmetric Discovery feed
curl -s "http://localhost:8001/discovery/asymmetric?limit=10" | jq

# 8. Chat (auth required)
USER_ID=$(curl -s http://localhost:8001/auth/me -H "Authorization: Bearer $TOKEN" | jq -r .id)
curl -s -X POST http://localhost:8001/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\",\"query\":\"Analyse Reliance Industries\",\"expertise_level\":\"intermediate\"}" \
  | jq '.response' | head -40
```

UI smoke test: http://localhost:5173 → sign up → Home shows your (empty) watchlist + the platform asymmetric feed → search "Reliance" → click → broker-style stock page renders with a 1Y candle chart.

---

## 6. Feature guide

### 6.1 Auth & profile

Mandatory. Argon2id password hashing, JWT access (15 min) + refresh (30 d) with rotation.

```bash
# Signup
curl -X POST http://localhost:8001/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123","username":"you","full_name":"You"}'

# Login (email or username works as identifier)
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"you@example.com","password":"password123"}'

# Refresh
curl -X POST http://localhost:8001/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"..."}'

# Logout (blacklists access token; revokes refresh if supplied)
curl -X POST http://localhost:8001/auth/logout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"..."}'

# Me
curl http://localhost:8001/auth/me -H "Authorization: Bearer $TOKEN"

# Forgot password (logs the reset URL when EMAIL_SENDER=stub)
curl -X POST http://localhost:8001/auth/forgot-password \
  -H "Content-Type: application/json" -d '{"email":"you@example.com"}'

# Reset password
curl -X POST http://localhost:8001/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<from email>","new_password":"newpassword123"}'
```

Rate limits: 5 logins / minute / IP, 3 signup + forgot / minute / IP. Returns 429 on excess.

### 6.2 Personalised Home

`GET /home/personalized` returns watchlist + holdings + asymmetric Discovery feed + recent timeline + suggestions in one shot. 60s Redis cache.

```bash
curl http://localhost:8001/home/personalized -H "Authorization: Bearer $TOKEN" | jq
```

The frontend's HomeView is the default landing surface after login.

### 6.3 Broker-style stock page

Live ticker quote (10s polling), 1D / 1W / 1M / 6M / 1Y / 5Y / MAX candles (yfinance → Upstox → FMP fallback), peer grid, and an Ask-Minerva floating button.

```bash
curl http://localhost:8001/quotes/RELIANCE | jq
curl "http://localhost:8001/quotes/RELIANCE/candles?range=6M" | jq '.ohlcv | length'
curl http://localhost:8001/quotes/RELIANCE/peers | jq 'length'
```

### 6.4 Discovery / asymmetric feed

The Castrol-style killer feature.

```bash
# Catalogue
curl http://localhost:8001/discovery/themes | jq

# Companies tagged to a theme
curl "http://localhost:8001/discovery/themes/data_centre_lubricants/companies?asymmetric_only=true" | jq

# All themes for one company (with is_asymmetric flag)
curl "http://localhost:8001/discovery/companies/<company_uuid>/themes" | jq

# Platform-wide asymmetric feed
curl "http://localhost:8001/discovery/asymmetric?min_confidence=0.6&limit=20" | jq

# 1-hop graph neighbours of a theme (for second-order analysis)
curl http://localhost:8001/discovery/themes/ai_data_centres/neighbors | jq
```

The Discovery subagent fires for chat queries containing words like *hidden / asymmetric / non-obvious / second-order / ripple / who else benefits*.

### 6.5 Minerva chat

```bash
curl -X POST http://localhost:8001/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<your uuid>","query":"What hidden AI / data-centre exposure does Castrol India have?","expertise_level":"intermediate"}'
```

Response follows the structured skeleton: Domain & Subdomain Exposure → Hidden / Asymmetric Exposure → Growth / Cost Drivers → Financial Health → Risk Flags → Macro Sensitivity → Second-Order Effects → Bull vs Bear → Explained Simply → Sources → 3 Suggested Follow-ups.

Expertise level is read from the request body and / or `/memories/user_preferences.txt`. Beginner gets twice the layman depth; advanced gets terse + IRR/DCF/peer-multiples context.

### 6.6 Portfolio + broker OAuth

```bash
# Manual portfolio
curl -X POST http://localhost:8001/portfolios/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"user_id":"<your uuid>","name":"My Portfolio"}'

curl -X POST http://localhost:8001/portfolios/<id>/holdings \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"company_id":"<company uuid>","quantity":100,"average_price":2800}'

# Holdings count for the logged-in user (used by the dashboard widget)
curl http://localhost:8001/portfolios/me/holdings-count -H "Authorization: Bearer $TOKEN"

# Zerodha Kite OAuth — needs KITE_API_KEY / KITE_API_SECRET
curl http://localhost:8001/broker/zerodha/login-url -H "Authorization: Bearer $TOKEN"
# Redirect user to login_url; Kite calls back to .../broker/zerodha/callback?request_token=...
# After callback, sync:
curl -X POST http://localhost:8001/broker/portfolios/<portfolio_id>/sync \
  -H "Authorization: Bearer $TOKEN"
```

### 6.7 Watchlists, alerts, screens, timeline, news, document upload

All gated by JWT. `user_id` in the path/body must match the bearer token's subject (returns 403 otherwise).

- Watchlists: `GET /watchlists/?user_id=<self>`, `POST /watchlists/`, `POST /watchlists/{id}/companies`, `DELETE /watchlists/{id}/companies/{company_id}`.
- Alerts: same pattern. New `condition_type=asymmetric_theme` fires on a fresh `is_asymmetric` tag for any of the rule's `company_ids`.
- Screens: `POST /screens/run` now accepts `themes`, `min_theme_confidence`, `asymmetric_only`, `min_pe`, `max_pe`, `min_roe`, `max_debt_to_equity` on top of the legacy filters.
- Timeline: `GET /timeline/?company_id=&days=` reads AI-generated one-liners from `filing_summaries`.
- News: `GET /get-news?limit=&query=` (renamed from `/newsdata/...` in older docs).
- Document upload: `POST /chat/upload` (multipart `file=@...`, `user_id=<self>`).

### 6.8 Observability

```bash
curl http://localhost:8001/health     # {"status":"healthy"}
curl http://localhost:8001/ready      # 200 if all infra up; 503 if Postgres down
curl http://localhost:8001/metrics    # Prometheus exposition
```

Counters exposed: `agent_invocations_total{subagent,outcome}`, `tool_calls_total{tool}`, `cache_hits_total{cache}`, `cache_misses_total{cache}`, `etl_run_status_total{pipeline,status}`, `alerts_fired_total{condition_type}`, plus `http_request_duration_seconds` histogram.

Every API response carries an `X-Request-ID` header; logs are structured and include `request_id=...` so you can correlate.

---

## 7. API reference

All endpoints on a single backend at `:8001`. Routes marked **(auth)** require `Authorization: Bearer <jwt>`.

### Auth & user

| Method | Endpoint | Notes |
|---|---|---|
| POST | `/auth/signup` | argon2id, returns `{user, tokens, email_verification_required}` |
| POST | `/auth/login` | identifier = email or username |
| POST | `/auth/refresh` | rotates refresh; old jti is revoked |
| POST | `/auth/logout` (auth) | blacklists access; revokes refresh if supplied |
| POST | `/auth/forgot-password` | always 202 to avoid leaking account existence |
| POST | `/auth/reset-password` | consumes one-time token |
| POST | `/auth/verify-email` | consumes verification token |
| POST | `/auth/resend-verification` (auth) | re-sends email with fresh token |
| GET | `/auth/me` (auth) | current user record |
| GET | `/users/{user_id}` (auth, self) | profile |
| PUT | `/users/{user_id}` (auth, self) | profile update; invalidates Redis cache |
| POST | `/users/{user_id}/profile-pic` (auth, self) | avatar upload |
| POST | `/users/{user_id}/kyc/submit` (auth, self) | KYC submission |

### Quotes / candles / peers

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/quotes/{ticker}` | LTP + day range + OHLC; 15s cache |
| GET | `/quotes/{ticker}/candles?range=1D|1W|1M|6M|1Y|5Y|MAX&interval=` | tiered yfinance → Upstox → FMP |
| GET | `/quotes/{ticker}/peers` | same-industry / same-sector competitors |

### Discovery / themes

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/discovery/themes` | catalogue with company + asymmetric counts |
| GET | `/discovery/themes/{theme}/companies` | reverse lookup; supports `min_confidence`, `exposure_type`, `asymmetric_only` |
| GET | `/discovery/companies/{company_id}/themes` | active themes for a company |
| GET | `/discovery/asymmetric` | platform-wide Castrol-style feed |
| GET | `/discovery/themes/{theme}/neighbors` | theme→theme edges (1 hop) |
| GET | `/discovery/insights` | precomputed Insight Engine cards |
| GET | `/discovery/insights/metrics` | rolling per-type precision |
| GET | `/discovery/insights/{insight_id}` | one card with full evidence |

### Personalised home

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/home/personalized` (auth) | watchlist + holdings + asymmetric + timeline + suggestions, 60s cache |

### Companies, portfolio, broker, watchlists, alerts, screens, timeline, news, chat

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/companies/`, `/companies/search`, `/companies/{id}` | listings + lookups |
| GET | `/companies/{id}/quote`, `/financials`, `/ratios` | per-company data |
| POST | `/companies/{id}/refresh` | trigger an enrichment task |
| GET | `/portfolios/me/holdings-count` (auth) | distinct companies in user's holdings |
| GET | `/portfolios/?user_id=` (auth, self) | list |
| POST | `/portfolios/` (auth, self) | create |
| GET | `/portfolios/{id}` (auth, owner) | detail + holdings + metrics |
| POST | `/portfolios/{id}/holdings` (auth, owner) | upsert holding |
| GET | `/broker/zerodha/login-url` (auth) | OAuth start |
| GET, POST | `/broker/zerodha/callback` (auth, self) | exchange request_token for access_token |
| POST | `/broker/portfolios/{portfolio_id}/sync` (auth, owner) | pull holdings + write transactions |
| GET, POST, DELETE | `/watchlists/...` (auth) | unchanged contract, gated |
| GET, POST, DELETE | `/alerts/...` (auth) | new `asymmetric_theme` condition_type |
| POST | `/screens/run` (auth) | now accepts theme/ratio filters |
| GET | `/timeline/?company_id=&days=` | AI one-liners when available |
| GET | `/get-news?query=&limit=` | news feed |
| POST | `/chat/query` (auth, self) | router → subagents → synthesis |
| GET | `/chat/sessions/{user_id}` (auth, self) | thread list |
| POST | `/chat/upload` (auth, self) | multipart document upload |
| POST | `/compare/` (auth) | 2-5 company comparison |
| GET | `/health` | liveness |
| GET | `/ready` | readiness (Postgres + Redis + Qdrant) |
| GET | `/metrics` | Prometheus |

Interactive docs: http://localhost:8001/docs.

External-data proxy prefixes (auth not enforced; useful for the FE in unauthenticated contexts): `/fmp/...`, `/fred/...`, `/news/...`, `/newsdata/...`, `/upstox/...`, `/kite/...`.

---

## 8. LLM configuration

| Provider | `LLM_PROVIDER` | Default model | Key env vars |
|---|---|---|---|
| Groq | `groq` | `openai/gpt-oss-20b` | `GROQ_API_KEY` |
| Ollama | `ollama` | `deepseek-r1:8b` | `OLLAMA_BASE_URL` (default `http://localhost:11434`) |
| OpenAI | `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| DeepSeek | `deepseek` | `deepseek-chat` | `DEEPSEEK_API_KEY` |

Override the model regardless of provider with `LLM_MODEL=...` in `.env`.

The vision-LLM chart extractor in `src/etl/chart_extraction.py` requires either OpenAI or DeepSeek with vision support; it's gated behind `ENABLE_CHART_EXTRACTION=true`.

---

## 9. Database management

```bash
# Inspect
docker exec -it ai-equity-postgres-1 psql -U postgres -d equity_research
\dt
\d users
\d company_themes

# Migrations
cd backend-ai
alembic current
alembic upgrade head
alembic revision --autogenerate -m "describe your changes"

# Reset
docker compose down -v
docker compose up -d
cd backend-ai && alembic upgrade head
python scripts/seed_db.py
python scripts/seed_themes.py
```

---

## 10. Troubleshooting

**`401 Unauthorized` on `/chat/query` / `/portfolios/...`** — auth is mandatory now. Sign up via the UI, or POST to `/auth/signup` and use the `access_token` from the response as `Authorization: Bearer ...`. Tokens expire after 15 min; the frontend silently refreshes via `/auth/refresh`.

**`401` after working for a while** — access token expired and the refresh token is stale (or browser cleared `eq.refresh_token` from localStorage). Sign in again.

**`429 Too Many Requests` on login / signup / forgot** — slowapi rate limit hit. Wait 60s. Tunable via `AUTH_LOGIN_RATE_LIMIT` etc.

**`AUTH_JWT_SECRET` missing** — server starts but every login fails the moment it tries to sign a token. Set `AUTH_JWT_SECRET` in `.env` (generate with `openssl rand -hex 32`).

**Reset / verify emails not arriving** — `EMAIL_SENDER=stub` (the dev default) only logs the URL to stdout. Look in the uvicorn terminal for `[email-stub] to=... subject=Verify ...`. For real emails set `EMAIL_SENDER=smtp` or `ses` and provide the corresponding credentials.

**`ready: false` from `/ready`** — check the per-component sub-objects. Postgres failure is the only one that returns 503 (it's the hard dependency); Redis / Qdrant down still return 200 because the app degrades gracefully.

**Chart shows "No price data available"** — yfinance has rate limits; first call after a long pause sometimes returns empty. Retry in 30s. Set `FMP_API_KEY` to enable the second-tier fallback.

**Discovery feed is empty** — the asymmetric tagger hasn't run yet. Either ingest some filings/news/transcripts then run `etl.tag_themes`, or seed manually:

```bash
python -c "from src.agents.etl_agents.theme_agent import ThemeTaggingAgent; print(ThemeTaggingAgent().tag_universe(limit=50))"
```

**`Could not connect to backend` in the frontend** — backend not on `:8001`, or CORS issue. Check `curl http://localhost:8001/health`. The frontend ships `VITE_BACKEND_URL` configurable.

**psycopg2 build fails** — on macOS: `brew install postgresql`. Or downgrade to Python 3.11/3.12 for prebuilt wheels.

**`Cannot find module '@tanstack/react-query'` in the IDE** — frontend deps are declared but not yet installed. Run `npm install` in `frontend/`.

**Port 8001 in use** — `kill $(lsof -ti:8001)` or run on a different port (`--port 8002`) and update `frontend/.env`.

---

## 11. Project structure

```
ai-equity/
├── backend-ai/                          # FastAPI + LangGraph backend (port 8001)
│   ├── alembic/versions/                # 4 idempotent migrations
│   ├── src/
│   │   ├── app/                         # Factory, lifespan, middleware, router registration
│   │   ├── agents/                      # Orchestrator, 11 subagents, prompts, tools
│   │   │   ├── orchestrator.py
│   │   │   ├── subagents/               # company, comparison, discovery, portfolio, news,
│   │   │   │                            # doc_insight, policy_macro, theme_explorer,
│   │   │   │                            # transcript_analyst, macro_commodity, graph_reasoning
│   │   │   ├── prompts/                 # System prompts (incl. structured-output skeleton)
│   │   │   ├── tools/                   # Financial, vector_search, themes, discovery,
│   │   │   │                            # relations, insights, transcripts, macro, social, etc.
│   │   │   ├── etl_agents/              # Offline LLM agents (theme tagger, event extractor,
│   │   │   │                            # insight discoverer, supply_chain, pattern_mining)
│   │   │   ├── memory.py                # Composite store + checkpointer + skill seeding
│   │   │   └── skills/
│   │   ├── domains/                     # API surface, organised by feature
│   │   │   ├── auth/                    # Round 2: argon2id + JWT + email
│   │   │   ├── home/                    # Round 2: /home/personalized
│   │   │   ├── quotes/                  # Round 2: ticker-keyed quote / candles / peers
│   │   │   ├── broker/                  # Zerodha OAuth + portfolio sync
│   │   │   ├── discovery/               # /discovery/* (themes + asymmetric)
│   │   │   ├── chat/, companies/, compare/, portfolio/,
│   │   │   ├── alerts/, watchlists/, screens/, timeline/,
│   │   │   ├── news/, users/, insights/
│   │   ├── services/
│   │   │   ├── cache_service.py         # Redis + user-profile cache helpers
│   │   │   ├── visualization_service.py # Plotly chart PNGs
│   │   │   ├── financial_service.py, news_service.py, portfolio_service.py,
│   │   │   ├── document_processor.py, vector_service.py, gemini_enrichment_service.py,
│   │   │   └── market_data/
│   │   │       ├── quotes_service.py, financials_service.py, ratios_service.py,
│   │   │       ├── enrichment_service.py, historical_service.py    # tiered candles
│   │   │       └── helpers.py
│   │   ├── integrations/market_data/    # FMP, FRED, Kite, Upstox, NewsAPI, NewsDataIO adapters
│   │   ├── etl/
│   │   │   ├── tasks.py                 # Celery task registry
│   │   │   ├── crawler_nse.py, crawler_ir.py, news_ingest.py, social_ingest.py,
│   │   │   ├── transcript_ingest.py, macro_ingest.py, sentiment.py, doc_parser.py,
│   │   │   ├── chart_extraction.py, filing_summary.py, theme_taxonomy_loader.py,
│   │   │   ├── alert_evaluator.py, monitoring.py    # stuck reaper + new-listing
│   │   │   ├── confidence.py, source_registry.py, guardrails.py, sector_commodity_loader.py
│   │   ├── db/                          # SQLAlchemy session + models
│   │   ├── llm/                         # LLM + embedding factories
│   │   ├── schemas/
│   │   │   └── structured_analysis.py   # 14-section response contract
│   │   ├── observability.py             # counters + readiness
│   │   ├── config.py                    # Pydantic settings (incl. all auth + email vars)
│   │   └── main.py
│   ├── scripts/                         # seed_db.py, seed_themes.py, run_agent.py, debug_run.py
│   └── requirements.txt
│
├── frontend/                            # React 19 + Vite SPA (port 5173)
│   ├── src/
│   │   ├── main.tsx                     # AuthProvider + RequireAuth + QueryProvider wrap
│   │   ├── App.tsx                      # Default view = "home"
│   │   ├── app/
│   │   │   ├── components/AppContentRouter.tsx
│   │   │   ├── components/SidebarShell.tsx
│   │   │   └── state/                   # AuthContext, RequireAuth, QueryProvider
│   │   ├── features/
│   │   │   ├── auth/                    # SignUp, Login, Forgot, Reset, AuthGate
│   │   │   ├── home/HomeView.tsx
│   │   │   ├── company/
│   │   │   │   ├── CompanyWorkspaceView.tsx   # legacy view
│   │   │   │   └── broker/              # BrokerStockPage + StockChart + QuoteHeader
│   │   │   │                            # + RangeToggle + PeersTab + AskMinervaFAB
│   │   │   ├── chat/, dashboard/, discovery/, filings/, news/,
│   │   │   ├── portfolio/, profile/, settings/, timeline/, compare/
│   │   ├── components/OmniSearch.tsx
│   │   ├── shared/api/                  # core.ts (auth interceptor) + auth.ts + home.ts +
│   │   │                                # quotes.ts + platform.ts + external.ts + user.ts
│   │   ├── lib/api.ts                   # legacy compatibility surface
│   │   └── index.css                    # CSS variables
│   ├── package.json                     # incl. @tanstack/react-query, lightweight-charts
│   └── vite.config.ts
│
├── plans/
│   ├── SHIPPED.md                       # *** start here for what's actually built ***
│   ├── 07_round2_broker_grade_plan.md   # Round 2 plan + locked decisions
│   ├── ARCHITECTURE_OVERVIEW.md
│   ├── README.md                        # plans index
│   └── 00–06 (historical design)
│
├── docker-compose.yml                   # Postgres + Redis + Qdrant
└── README.md, GETTING_STARTED.md, AGENTS.md
```
