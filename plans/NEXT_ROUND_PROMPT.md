# Planning Prompt — Round 2 (ETL + Frontend + Performance + Auth)

Paste this as the user message in plan mode to kick off the next gap-analysis + planning round.

---

## Role

You are a senior staff-level full-stack architect picking up an in-flight project. Your job is to: (a) audit current state, (b) propose a clean phased plan, (c) once approved, build to production quality. You have already completed Round 1 (the "Hidden Insights & Industries" Discovery vertical, governance flags, timeline summarizer, broker OAuth, alert evaluator, visualization service, structured-output schema) — see `plans/run-a-codebase-scan-snappy-avalanche.md` for what's done.

## Context

**Repo:** `/Users/shamanthh/Downloads/ai-equity-1`
**What it is:** AI-native equity research platform for Indian retail investors. Minerva (chat assistant) + Discovery (asymmetric theme insights) + Portfolio (broker-connected analytics) + Timeline (AI-curated NSE/BSE filings).
**Stack today:** Python 3.11 / FastAPI / LangGraph (via DeepAgents) / Postgres / Qdrant / Redis / Celery+SQS / AWS / React+Vite frontend.
**What's built (Round 1):** ~75% of the agent + data backbone. Discovery + theme tagger + risk flags + timeline + broker OAuth + alert evaluator + viz service all live.
**Gap:** ETL coverage / orchestration choice; frontend feature completeness; speed / streaming / caching; user auth & profile UX; FE↔BE wiring audit.

## Objective

Close all remaining gaps so the platform is **(a) genuinely autonomous in data ingestion, (b) feels as polished as Groww/Zerodha/Angel One on stock detail pages, (c) responds fast with progressive streaming, (d) has solid auth and personalised home experience.**

## Scope — investigate and plan for each area

### 1. ETL pipeline gap analysis

- **Orchestration choice.** Current is Celery + SQS (OSS, free). Decide whether that's sufficient or whether we should adopt one of: **Apache Airflow** (OSS, self-host), **Prefect** (OSS Cloud free tier), **Dagster** (OSS), **AWS Glue / MWAA**, **Azure Data Factory**, or **Databricks Workflows**. Recommend ONE with clear trade-off rationale (lineage, retries, observability, cost, learning curve, India-AWS region availability).
- **Coverage audit.** For each source, confirm a periodic job exists, runs idempotently, and covers what we need:
  - NSE corporate announcements (daily)
  - BSE corporate announcements (daily) — verify, current code may only cover NSE
  - IR site auto-discovery + crawl (weekly)
  - Annual reports / 10-K equivalents
  - Concall transcripts + audio (where available)
  - Investor presentations
  - Shareholding pattern filings (quarterly)
  - Insider / promoter trading disclosures
  - Board-meeting outcomes
  - News (GNews, NewsAPI, RSS — hourly)
  - Social signals (Reddit, X, StockTwits) — confirm running
  - Macro series (FRED, RBI, commodity)
- **Document processing depth.** Verify table extraction, chart extraction, sentiment, embeddings, theme tagging, filing summarisation all chain end-to-end and have backlog drainers.
- **Self-discovery.** Is there a job that finds new listings (IPOs, recent listings) and bootstraps their crawl pipeline automatically?
- **Failure handling.** DLQ? Alert-on-stuck-pipeline? Retry policy?
- **Cost & scale.** ~5,000 listed Indian companies × ~50 docs/year = 250K docs/year. Estimate cost on the chosen orchestrator at this scale.
- **Output:** decision matrix (Airflow vs Celery vs MWAA vs Prefect vs Dagster), recommendation, migration plan (or rationale to stay on Celery and just harden it).

### 2. Agentic backend completeness

- **Tools per subagent.** Audit each of the 11 subagents (`company`, `comparison`, `discovery`, `portfolio`, `news`, `doc-insight`, `policy-macro`, `theme-explorer`, `transcript-analyst`, `macro-commodity`, `graph-reasoning`). For each: list assigned tools, identify missing tools, identify duplicated capability across subagents.
- **Prompt quality.** Each subagent prompt should have: clear role, single responsibility, exact tool-call workflow, output skeleton matching the platform-wide structured schema, expertise-level adaptation, evidence-citation rule. Score each prompt 1–5 and flag the gaps.
- **MCP exposure.** Decide whether to expose key tools (theme search, company facts, asymmetric feed, portfolio metrics) as a public **MCP server** so external clients (Claude Desktop, third-party agents) can consume them. If yes: which tools, transport (stdio vs HTTP), auth model, rate limits.
- **Streaming.** Today the agent invocation is blocking. Propose a streaming-token interface (SSE) so the chat UI can render progressively (ChatGPT-style "show as you receive").
- **Parallel tool execution.** When a query needs multiple independent tool calls (financials + ratios + news for one company), fire them in parallel via `asyncio.gather` rather than sequential — quantify expected latency win.

### 3. Frontend completeness

- **Audit the existing frontend** (`frontend/`) — read `App.tsx`, `lib/api.ts`, every feature folder, every page route. List what's present, broken, missing.
- **Frontend ↔ backend wiring matrix.** For every backend route in `src/app/routers.py`, confirm there's a frontend caller and a UI surface. Flag every dangling endpoint and every UI surface that should call something but doesn't.
- **Home / Search experience.**
  - Show the user's portfolio holdings + watchlist companies as the *default* search results when the search box is empty.
  - "Trending themes" rail powered by `/discovery/asymmetric`.
  - Recent timeline strip powered by `/timeline/`.
- **Broker-style stock detail page.** When a user clicks into a company, show:
  - Live LTP + day range + open/close/high/low.
  - **Price chart** with toggles: 1D / 1W / 1M / 6M / 1Y / 5Y / Max. Candlestick OR line, user choice. Volume bars below.
  - **Color-coded line/area:** green when above prior close, red when below — gradient fill underneath.
  - Smooth time-axis pan/zoom (Plotly or Recharts or lightweight-charts).
  - Tabs: Overview / Financials / Ratios / Filings / Themes (with asymmetric badge) / News / Peers / Concall transcripts / Discovery insights.
  - Buy/Sell action buttons that deep-link to the connected broker (Zerodha kite.zerodha.com URL with the symbol prefilled).
  - "Ask Minerva" floating CTA scoped to the company (pre-fills chat with `company_id` context).
- **Data sources for charts.** Use existing endpoints first (`/companies/{id}/quote`, `/companies/{id}/financials`); if intraday/historical OHLC isn't there, integrate one of: **Yahoo Finance via `yfinance`**, **Upstox** (already wrapped), **Kite Connect historical** (needs API key), **NSE-India reverse-engineered**, or **Alpha Vantage** (free 25 req/day). Recommend ONE and add the integration.
- **Chat UX.** ChatGPT-style: SSE streaming, "Minerva is thinking…" skeleton, "Sources" / "Suggested follow-ups" rendered as side-cards, message-level retry / regenerate.
- **Loading strategy.** Skeleton screens, route-based code splitting, react-query stale-while-revalidate, infinite-scroll pagination on Timeline / News / Discovery feeds.

### 4. Performance & speed

- **Backend.** Identify endpoints currently doing N+1 queries or sync IO; convert to `async def` + `asyncio.gather` where multiple awaits are independent. Verify every route uses the existing `Depends(get_db)` async pattern.
- **Worker pools.** Right-size Celery worker pools: separate queues already exist (`crawlers / parsers / embeddings / news / theme_tagging / alert_eval`); set autoscaling rules per queue.
- **Caching.** Redis for: user profile (15 min TTL), `/companies/{id}/quote` (60 sec TTL), `/discovery/asymmetric` (10 min TTL), agent responses keyed by `(user_id, query_hash, last_filing_id)` (1 hour TTL with smart invalidation). Plan exact cache keys and invalidation triggers.
- **Frontend.** Code-split per route, prefetch on hover, virtual scroll for long lists, debounced search, react-query cache.
- **Streaming.** SSE on `/chat/query` so the UI renders tokens as they arrive. Today's blocking response should remain as a fallback for non-streaming clients.

### 5. User profile & auth

- **Schema.** `users` table already has `email`, `username`, `password_hash`, `expertise_level`. Confirm + extend (avatar, theme preference, default chart range, default expertise, sectors of interest).
- **Auth flow.** Signup → email verification → login (JWT access + refresh tokens) → password reset. Use `passlib[bcrypt]` for hashing; `python-jose` for JWT. FastAPI `Depends` middleware for auth on every non-public route.
- **Frontend.** Signup, login, forgot-password, profile-edit, settings pages. Token storage (httpOnly cookie preferred over localStorage).
- **Profile cache.** Hot-cache the JWT-resolved user record in Redis under `user:{user_id}:profile`, 15-min TTL, invalidated on PATCH.
- **Session memory.** Confirm chat session memory still works after auth is gated.

### 6. Observability & operational hygiene

- Confirm structured logging (`structlog`) is on every new service.
- Add Prometheus / OpenTelemetry counters for: agent invocations, tool calls, cache hit-rate, ETL run status, alert firings.
- Health-check endpoints per service (`/health`, `/ready`).

## Deliverables (planning phase)

1. **Gap matrix** (markdown table): `area | requirement | current state | gap | priority (P0/P1/P2) | effort (S/M/L)`.
2. **Architecture decisions**: orchestrator pick, MCP yes/no with rationale, streaming protocol pick (SSE vs WebSocket), auth scheme, chart library pick.
3. **Phased plan** with concrete file paths and reuse-don't-rebuild notes (mirror the style of `plans/run-a-codebase-scan-snappy-avalanche.md`).
4. **Verification plan** — for each phase: how to test (curl / browser / pytest / load-test).
5. **Out-of-scope list** — what we explicitly defer.

## Constraints

- **OSS-first.** Every paid SaaS choice must be justified vs an OSS alternative.
- **India-only for now** (NSE/BSE/INR). US-market features deferred.
- **Reuse over rewrite.** The Round 1 components (theme tagger, discovery subagent, structured schema, broker domain) stay; extend, don't fork.
- **No frontend rewrite.** Augment the existing React+Vite app; don't migrate to Next.js or Remix.
- **Backwards-compatible API.** Existing routes must keep their URL + response shape; new fields are additive.
- **Cost ceiling MVP**: ~$500/month all-in.

## Workflow

1. Read this prompt, then run a fresh codebase scan with parallel `Explore` agents focused on ETL, frontend, and connectivity.
2. Verify findings against the actual files (don't trust agent summaries blindly).
3. Use `AskUserQuestion` for any architecture forks where you're 50/50 (e.g. Recharts vs Lightweight-charts; Airflow vs hardened Celery).
4. Write the final plan to the plan file the harness creates. Call `ExitPlanMode` when ready.
5. Once approved, implement in the recommended order. Track progress with `TodoWrite`. Compile-check every changed file. Run `pytest` if available. Stop at the end of each phase to confirm.

## Definition of done (overall)

- A new user can sign up, log in, see their watchlist + holdings on the home page, click into Reliance, see a 1Y candlestick coloured by daily change, browse Financials/News/Themes/Discovery tabs, ask Minerva a question and watch the answer stream token-by-token with sources + 3 follow-ups.
- Every backend route is exercised by some frontend surface (or explicitly marked internal/admin).
- ETL pipelines run nightly without intervention, surface failures in CloudWatch, and ingest at least Annual Reports + Concalls + News + Filings + Shareholding for the entire NSE-listed universe.
- p95 chat-query latency stays under 3 seconds with streaming first-token under 500 ms.
- Test suite remains green; new services have at least one integration test each.
