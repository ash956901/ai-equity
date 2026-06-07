# Minerva — Technical Reference Document

**Project:** Minerva — AI-Native Equity Research Platform
**Team:** Ashutosh Kumar (1MS22CS036) · Sanchit Vijay (1MS22CS122) · Shamanth M. Hiremath (1MS22CS128)
**Guide:** Dr. Chandrika Prasad, Dept. of CSE, M.S. Ramaiah Institute of Technology
**Last updated:** 2026-06-02 · **Codebase root:** `ai-equity/`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Technology Stack — Full Inventory](#3-technology-stack--full-inventory)
4. [External Data Sources — API Integration Catalog](#4-external-data-sources--api-integration-catalog)
5. [ETL Pipeline — Deep Dive](#5-etl-pipeline--deep-dive)
6. [Database Layer](#6-database-layer)
7. [AI Agent System — Hierarchy](#7-ai-agent-system--hierarchy)
8. [Agent Tools — Manifest](#8-agent-tools--manifest)
9. [LangGraph State Machine](#9-langgraph-state-machine)
10. [Deep Agents — Why and How](#10-deep-agents--why-and-how)
11. [LLM & Embedding Strategy](#11-llm--embedding-strategy)
12. [RAG Pipeline — End to End](#12-rag-pipeline--end-to-end)
13. [Causal Intelligence Engine](#13-causal-intelligence-engine)
14. [Frontend Architecture](#14-frontend-architecture)
15. [Performance & Benchmarks](#15-performance--benchmarks)
16. [Security & Compliance](#16-security--compliance)
17. [Deployment Topology](#17-deployment-topology)
18. [Anticipated Q&A — Defensive Reference](#18-anticipated-qa--defensive-reference)

---

## 1. Executive Summary

Minerva is an AI-native autonomous equity research platform built specifically for Indian equity markets (NSE / BSE). It ingests live regulatory filings, news, financial fundamentals, commodity prices, and geopolitical events; stores them in a polyglot database stack; and answers natural-language research queries through a hierarchical multi-agent AI system where every answer is citation-grounded to its source document.

**Five architectural differentiators:**
- **Citation-grounded RAG** — every numerical claim is traceable to a source row or document passage; claims that cannot be sourced are dropped before the answer reaches the user.
- **Hierarchical multi-agent orchestration** — a central LLM orchestrator (IRIS) routes queries to 8 domain-specialist sub-agents, each with its own memory, planning loop, and restricted tool manifest.
- **Semantic ETL pipeline** — automated, section-aware document chunking and embedding pipeline running on 9 Celery Beat schedules, covering NSE/BSE filings, news, and commodity prices.
- **Causal Intelligence Engine** — 11 geopolitical-to-commodity-to-sector causal chains that proactively surface hidden portfolio risks.
- **Gamified Paper-Trading Simulator** — risk-free, XP/badge/streak-driven simulator backed by live market data, designed to lower the barrier to financial literacy.

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 6 — FRONTEND          React 19 + TypeScript 5.8  │
│            Port 5173          Vite · Tailwind · Recharts │
├─────────────────────────────────────────────────────────┤
│  LAYER 5 — API GATEWAY       FastAPI 0.115 + Uvicorn    │
│            Port 8001          Pydantic 2.10 · 60+ routes │
├─────────────────────────────────────────────────────────┤
│  LAYER 4 — AGENT SYSTEM      DeepAgents 0.4 + LangGraph │
│            IRIS orchestrator  8 sub-agents · 11 tools    │
├─────────────────────────────────────────────────────────┤
│  LAYER 3 — DATA STORAGE      PostgreSQL · Qdrant · Redis │
│                               MongoDB (optional)         │
├─────────────────────────────────────────────────────────┤
│  LAYER 2 — ETL PIPELINE      Celery 5.4 + Celery Beat   │
│            9 scheduled tasks  3 swim lanes               │
├─────────────────────────────────────────────────────────┤
│  LAYER 1 — EXTERNAL SOURCES  NSE · BSE · FMP · FRED     │
│            10 APIs            NewsAPI · AV · GDELT · ...  │
└─────────────────────────────────────────────────────────┘
```

| Layer | Responsibility | Primary Technology | Entry Point |
|---|---|---|---|
| External Sources | Raw data acquisition | 10 REST APIs | `backend-ai/src/integrations/` |
| ETL Pipeline | Ingest, parse, chunk, embed, enrich | Celery 5.4, Ollama, Gemini | `backend-ai/src/etl/` |
| Data Storage | Persistence, caching, vector index | PostgreSQL 15, Qdrant, Redis 7 | `backend-ai/src/db/` |
| Agent System | Reasoning, retrieval, synthesis | DeepAgents 0.4, LangGraph 0.3 | `backend-ai/src/agents/` |
| API Gateway | HTTP interface, auth, routing | FastAPI 0.115, Uvicorn | `backend-ai/src/main.py` |
| Frontend | User interface, streaming chat | React 19.1, TypeScript 5.8 | `frontend/src/` |

---

## 3. Technology Stack — Full Inventory

| Layer | Component | Technology & Version | Why This / Not Alternative |
|---|---|---|---|
| Backend framework | HTTP server | FastAPI 0.115 | Native async, automatic OpenAPI docs, Pydantic integration. Flask lacks native async; Django is overpowered for an API-only service. |
| Backend runtime | ASGI server | Uvicorn (latest) | Best performance with FastAPI; Gunicorn+sync is slower for I/O-bound LLM calls. |
| Data validation | Schema layer | Pydantic 2.10 | Pydantic v2 uses Rust core — 5–20× faster than v1. |
| ORM | DB abstraction | SQLAlchemy 2.0 | Mature, supports async sessions, clean mapper syntax. Django ORM is tied to Django. |
| DB migrations | Schema versioning | Alembic | Standard SQLAlchemy companion; supports auto-generate and rollback. |
| Agent orchestration | Multi-agent framework | DeepAgents 0.4.12 + LangGraph 0.3.0 | DeepAgents provides sub-agent isolation and tool-masking on top of LangGraph's stateful graph. CrewAI lacks fine-grained action masking; AutoGen is research-grade and brittle. |
| Agent state | State machine | LangGraph 0.3.0 | DAG with conditional edges + native checkpointing. LangChain Expression Language alone has no persistent state. |
| Task queue | Background jobs | Celery 5.4.0 | Industry-standard Python task queue with beat scheduler. RQ is simpler but lacks cron scheduling. |
| Message broker | Queue backend | Redis 7 (via redis-py 5.0) | Sub-millisecond pub/sub; doubles as result backend and analysis cache. RabbitMQ is heavier for this use case. |
| Primary DB | Relational store | PostgreSQL 15 | JSONB support for semi-structured data, mature ACID guarantees, strong Alembic tooling. MySQL lacks JSONB natively. |
| Vector DB | Embedding store | Qdrant 1.12 | Self-hosted, HNSW indexing, filterable payload, no vendor lock-in. Pinecone is SaaS-only (data residency concern); Weaviate is heavier to operate. |
| Optional DB | Document store | MongoDB (motor async) | For Netflix-style multi-profile JSON storage. Initialized lazily only if `MONGODB_URI` is set. |
| Embedding model | Text vectorization | nomic-embed-text (768-dim) via Ollama | Runs locally; high quality for financial text. OpenAI text-embedding-3-small is a paid fallback. |
| LLM inference | Primary reasoning | Configurable (see §11) | Provider-agnostic via middleware pattern. |
| ETL enrichment | Structured extraction | Gemini 2.5 Flash | Low cost per document for batch enrichment (summaries, red flags, key metrics). Not used for interactive inference. |
| News NLP | Sentiment | FinBERT (HuggingFace) | Domain-trained on financial text; better recall on earnings language than general-purpose BERT. |
| News NLP | Topic classification | DistilBERT-MNLI | Zero-shot topic tagging without fine-tuning. |
| Frontend framework | SPA | React 19.1 | Concurrent features, Suspense, native streaming support. Vue 3 and Svelte are viable but the team had stronger React proficiency. |
| Frontend bundler | Build tool | Vite 6 | ESM-native, ~10× faster HMR than Webpack/CRA. |
| Frontend styling | CSS | Tailwind CSS | Utility-first; eliminates specificity wars. Not CSS-in-JS to avoid runtime overhead. |
| Frontend charts | Visualization | Recharts 3.8 + Chart.js 4.5 | Recharts for declarative charts in JSX; Chart.js for canvas-based performance when rendering large datasets. |
| Frontend testing | Unit tests | Vitest 3.2 | Same config as Vite; Jest is slower with Vite projects. |
| Type system | Frontend safety | TypeScript 5.8 | Strict mode; zero-error CI gate (`npx tsc --noEmit`). |
| Containerization | Local dev infra | Docker Compose | One `docker-compose.yml` spins up Postgres, Redis, Qdrant. |

---

## 4. External Data Sources — API Integration Catalog

| Provider | Data Type | Key Endpoints Used | Auth | Failure Strategy | Code Path |
|---|---|---|---|---|---|
| **NSE India** | Corporate filings, announcements | Filing XML feed, corporate action announcements | Public / session cookie | Retry with exponential backoff; stale data flagged in `etl_runs` | `src/etl/crawler_nse.py` |
| **BSE India** | Corporate filings | BSE filings download API | Public | Same as NSE; dual-source deduplication | `src/etl/crawler_bse.py` |
| **Financial Modeling Prep (FMP)** | Fundamentals, ratios, earnings, dividends | Income statement, balance sheet, cash flow, key metrics, ratios, earnings calendar, SEC filings screener (30+ endpoints) | API key (`FMP_API_KEY`) | Cached in PostgreSQL; stale threshold = 24 h | `src/integrations/market_data/providers/FMP_api/client.py` |
| **FRED (Federal Reserve)** | Macro indicators | Series observations (GDP, CPI, interest rates) | API key (`FRED_API_KEY`) | Macro data is low-frequency; serve from cache on failure | `src/integrations/market_data/providers/FRED_api/` |
| **NewsAPI** | Global headlines | `/v2/everything`, `/v2/top-headlines` | API key (`NEWS_API_KEY`) | Fall through to NewsData.io; log degraded state | `src/integrations/market_data/providers/NewsAPI/` |
| **NewsData.io** | Global + regional news | `/api/1/news` | API key (`NEWSDATA_API_KEY`) | Secondary source; combined with NewsAPI in aggregator | `src/integrations/news_client.py` |
| **Alpha Vantage** | Commodity prices | WTI crude, Brent crude, natural gas, gold, silver via `COMMODITY` function | API key (`ALPHA_VANTAGE_API_KEY`) | Yahoo Finance (yfinance) fallback | `src/etl/commodity_sync_task.py` |
| **GDELT** | Geopolitical events | GDELT GKG v2 event stream | Public (no key) | Skip cycle on timeout; events are additive, not blocking | `src/etl/event_monitor_task.py` |
| **Upstox** | Live market quotes (NSE/BSE) | Market quotes, OHLCV intraday | OAuth2 (`UPSTOX_API_KEY`, `UPSTOX_ACCESS_TOKEN`) | Fall through to Kite; serve last-known quote with staleness flag | `src/integrations/market_data/upstox.py` |
| **Kite / Zerodha** | Live market quotes | Quote API, historical data | API key + access token (`KITE_API_KEY`, `KITE_ACCESS_TOKEN`) | Fall through to FMP delayed quote | `src/integrations/market_data/kite.py` |

**Design note:** All API clients implement a common interface defined in `src/integrations/market_data/context.py` (`MarketDataContext`). The orchestration layer never calls any provider directly — it goes through the context object, which handles retry, fallback, and logging transparently.

---

## 5. ETL Pipeline — Deep Dive

### 5.1 Three Swim Lanes

**Lane A — Document Ingestion** (`src/etl/crawler_*.py`, `src/etl/document_processor.py`)

Responsible for all unstructured-text ingestion from NSE, BSE, and investor-relations pages. Raw PDFs are fetched, parsed with PyMuPDF and pdfplumber (fallback), stripped of noise, and split into semantic chunks. The chunking strategy is section-aware: the processor looks for structural headers (`Risk Factors`, `Management Discussion and Analysis`, `Financial Statements`, etc.) before falling back to fixed 512-token windows with 50-token overlap. Each chunk is assigned a content hash — identical content re-ingested from a different crawl cycle is deduplicated at the load step. Chunks are embedded and loaded into Qdrant collection `company_filings`.

**Lane B — Market Data Sync** (`src/etl/tasks.py`)

Handles all structured numerical data: NSE/BSE stock universe, company fundamentals from FMP, financial ratios, and commodity prices from Alpha Vantage. Output lands in PostgreSQL tables. Company enrichment (LLM-powered extraction of a business summary, competitive position, and red flags) uses Gemini 2.5 Flash for cost efficiency over GPT-4.

**Lane C — News & Events** (`src/etl/news_sync_task.py`, `src/etl/event_monitor_task.py`, `src/etl/portfolio_news_task.py`)

Pulls news from NewsAPI and NewsData.io, classifies each article using FinBERT (sentiment) and DistilBERT-MNLI (zero-shot topic), and writes results to `news_articles` and `classified_news`. The GDELT monitor writes to `geopolitical_events`. Portfolio-news correlation runs every 30 minutes and generates alerts for holdings with material news hits.

### 5.2 Celery Beat Schedule

| Task Name | Schedule | Lane | Writes To |
|---|---|---|---|
| `sync-stock-universe-daily` | Daily 06:00 IST | B | `companies`, `securities`, `exchanges` |
| `enrich-companies-daily` | Daily 07:00 IST (batch_size=100) | B | `companies` (summary, metrics, red flags) |
| `refresh-financials-morning` | Daily 08:00 IST | B | `financial_statements_raw`, `financial_ratios` |
| `refresh-financials-evening` | Daily 18:00 IST | B | `financial_statements_raw`, `financial_ratios` |
| `crawl-nse-filings-periodic` | Daily 09:30 IST | A | `filings`, `document_chunks`, Qdrant |
| `crawl-bse-filings` | Daily 09:00 + 15:00 IST | A | `filings`, `document_chunks`, Qdrant |
| `crawl-ir-pages-weekly` | Saturday 02:00 IST | A | `filings`, `document_chunks`, Qdrant |
| `sync-news-every-6-hours` | Every 6 h at :30 | C | `news_articles`, `classified_news` |
| `check-portfolio-news` | Every 30 min | C | `market_signals`, `alert_rules` (trigger) |

**Celery configuration:** broker = Redis `db/0`; result backend = Redis `db/1`; task time limit = 3600 s (soft 3300 s); timezone = `Asia/Kolkata`. Config file: `backend-ai/src/celery_app.py`.

### 5.3 Embedding Pipeline

1. `ETLTransformTask` (`src/etl/transform_task.py`) produces chunks with metadata (ticker, filing_date, doc_type, section, chunk_index, content_hash).
2. `EmbeddingGenerator` (`src/etl/embedding_generator.py`) calls Ollama's `nomic-embed-text` (768-dim) via `POST /api/embeddings`. If Ollama is unavailable, it falls back to OpenAI `text-embedding-3-small` (1536-dim, upcast at storage).
3. `ETLLoadTask` (`src/etl/load_task.py`) upserts vectors into Qdrant using `content_hash` as the point ID — idempotent by design.

---

## 6. Database Layer

### 6.1 PostgreSQL 15 — Table Groups

| Domain Group | Tables | Key Relationships |
|---|---|---|
| **Reference Data** | `companies`, `exchanges`, `securities`, `indices` | `securities.company_id → companies.id`; `securities.exchange_id → exchanges.id` |
| **Filings & Documents** | `filings`, `document_chunks` | `document_chunks.filing_id → filings.id`; `filings.company_id → companies.id` |
| **Financials** | `financial_statements_raw`, `financial_ratios` | Both reference `companies.id` and carry a `period_end` date |
| **Portfolio & Holdings** | `portfolios`, `holdings`, `user_transactions` | `holdings.portfolio_id → portfolios.id`; `holdings.company_id → companies.id` |
| **Chat** | `chat_sessions`, `chat_messages`, `user_uploads` | `chat_messages.session_id → chat_sessions.id` |
| **Alerts & Watchlists** | `alert_rules`, `market_signals`, `watchlists`, `watchlist_companies`, `saved_screens` | `alert_rules.user_id → users.id` |
| **News & Intelligence** | `news_articles`, `classified_news`, `commodity_prices`, `geopolitical_events` | `classified_news.article_id → news_articles.id` |
| **Causal** | `causal_chains`, `sector_exposures`, `causal_insights` | `causal_insights.chain_id → causal_chains.id` |
| **Simulator** | `simulated_trades`, `simulator_stats` | `simulated_trades.user_id → users.id` |
| **ETL Metadata** | `etl_runs`, `compare_flow_logs`, `company_comparison_snapshots` | `etl_runs` is append-only; no FK dependencies |
| **Users** | `users` | Root table; most domain tables reference `users.id` |

Connection pool: `pool_size=10`, `max_overflow=20`, async-safe via `asyncpg`. ORM models defined in `backend-ai/src/db/models.py`.

### 6.2 Qdrant

| Collection | Point ID | Embedding Dim | Distance | Payload Fields |
|---|---|---|---|---|
| `company_filings` | SHA-256 content hash | 768 | Cosine | `ticker`, `filing_date`, `doc_type`, `section`, `chunk_index`, `source_url`, `page_number` |
| `user_uploads` | UUID | 768 | Cosine | `user_id`, `session_id`, `filename`, `upload_date`, `chunk_index` |

HNSW index parameters use Qdrant defaults (`m=16`, `ef_construct=100`). Filtered search (e.g., `ticker == "RELIANCE"`) is executed via Qdrant's payload filter before cosine ranking. Client: `backend-ai/src/services/vector_service.py`.

### 6.3 Redis 7

| Usage | Key Pattern | TTL | Purpose |
|---|---|---|---|
| Analysis cache | `cache:{sha256(request_body)}` | 3600 s | Deduplicates identical chat / compare / causal requests | 
| Celery broker | Celery internal keys | N/A | Task queue for all 9 ETL tasks |
| Celery result | `celery-task-meta-{task_id}` | 86400 s | Stores task completion status and errors |

Cache implementation: `backend-ai/src/utils/cache.py` — SHA-256 of the serialised request body is the cache key. Cache misses incur full agent traversal; hits return in < 5 ms.

### 6.4 MongoDB (Optional)

Lazy-initialized via Motor async client (`backend-ai/src/db/mongo_client.py`). Only used when `MONGODB_URI` is set in environment. Stores Netflix-style user profiles (multiple named personas per account, each with independent portfolios and preferences). Falls back gracefully to local JSON files in `user-profiles/` if MongoDB is unavailable.

---

## 7. AI Agent System — Hierarchy

### 7.1 IRIS Orchestrator

Built via `build_research_agent()` in `backend-ai/src/agents/orchestrator.py`. IRIS is a DeepAgents `ResearchAgent` wrapping a LangGraph `StateGraph`. It receives the user query, classifies intent, enriches context (injecting user portfolio + session history from memory), and delegates to one or more sub-agents. Sub-agent results are merged and returned as a streamed response.

### 7.2 Specialist Sub-Agents

| Agent | File | Primary Responsibility | Primary Tools | System Prompt |
|---|---|---|---|---|
| **Company Analyst** | `subagents/company.py` | Fundamentals, ratios, LLM enrichment, red-flag detection | `financial_metrics`, `vector_search`, `document_analysis` | `prompts/company.py` |
| **Comparison Analyst** | `subagents/comparison.py` | Peer benchmarking, side-by-side metric comparison | `financial_metrics`, `resolve_company` | `prompts/comparison.py` |
| **Portfolio Manager** | `subagents/portfolio.py` | Beta (CAPM), Sharpe ratio, HHI diversification, volatility | `portfolio_metrics` | `prompts/portfolio.py` |
| **News Analyst** | `subagents/news.py` | News sentiment, filing-linked impact scoring, alert triggers | `news_retrieval`, `signal_engine` | `prompts/news.py` |
| **Document Reader** | `subagents/doc_insight.py` | RAG over Qdrant; dense passage retrieval from filings | `vector_search`, `document_analysis` | `prompts/doc_analysis.py` |
| **Thematic Explorer** | `subagents/thematic.py` | Cross-company semantic theme search (ESG, AI, export, etc.) | `vector_search`, `internet_search` | `prompts/thematic.py` |
| **Causal Detective** | `subagents/causal.py` | Geopolitical-to-sector domino chain analysis | `causal_tools`, `news_retrieval` | *(inline in subagent)* |
| **Performance Analyst** | `subagents/performance.py` | Return attribution, backtesting, benchmark comparison | `performance_tools`, `financial_metrics` | `prompts/performance.py` |

### 7.3 Why DeepAgents Over Alternatives

DeepAgents (v0.4.12) was chosen because it provides **sub-agent isolation with curated tool manifests** on top of LangGraph's graph execution model. Each sub-agent receives only the tools relevant to its domain at instantiation time — this is enforced at the framework level, not via prompt engineering alone. Neither CrewAI nor AutoGen offered this degree of action-space restriction combined with LangGraph's native checkpointing and streaming at the time of development.

---

## 8. Agent Tools — Manifest

| Tool | File | Input | Output | Backing Service |
|---|---|---|---|---|
| `resolve_company` | `tools/company_resolver.py` | Name or ticker string | `{company_id, ticker, exchange, sector}` | PostgreSQL `companies` table |
| `internet_search` | `tools/web_search.py` | Query string | List of search result snippets | Tavily API (`TAVILY_API_KEY`) |
| `vector_search` | `tools/vector_search.py` | Query string + optional ticker filter | Top-k document chunks with metadata | Qdrant `company_filings` |
| `document_analysis` | `tools/document.py` | Chunk IDs or raw text | Structured extraction (entities, figures, risk flags) | LLM call + Qdrant |
| `financial_metrics` | `tools/financial.py` | Ticker + metric names + date range | Dict of financial figures | PostgreSQL + FMP client |
| `portfolio_metrics` | `tools/portfolio.py` | List of `{ticker, weight}` | Beta, Sharpe, HHI, volatility, annualised return | PostgreSQL + local computation |
| `news_retrieval` | `tools/news.py` | Query or ticker + time window | List of classified news articles | PostgreSQL `classified_news` |
| `causal_tools` | `tools/causal_tools.py` | Event description or commodity name | Matching causal chains + affected sectors | PostgreSQL `causal_chains` + `sector_exposures` |
| `performance_tools` | `tools/performance_tools.py` | Portfolio + benchmark + date range | Attribution breakdown by sector/stock | PostgreSQL time-series data |
| `web_scraper` | `services/web_scraper.py` | URL | Cleaned text content | BeautifulSoup + httpx |
| `signal_engine` | `services/signal_engine.py` | Ticker or portfolio ID | Active market signals list | PostgreSQL `market_signals` |

---

## 9. LangGraph State Machine

### 9.1 State Schema (`src/agents/state.py`)

The agent state is a typed `TypedDict` carrying: `messages` (conversation history), `user_id`, `session_id`, `portfolio_context` (injected from DB), `active_subagents` (list of spawned sub-agent IDs), `tool_calls` (accumulator), `citations` (list of source references), and `final_answer` (set only when synthesis is complete).

### 9.2 Graph Topology

```
[START]
   │
   ▼
[intent_classifier]  ─── classifies into 7 intent types
   │
   ▼
[router]  ─────────────── conditional edges to sub-agents
   │                       based on intent + context
   ├──► [company_agent]
   ├──► [comparison_agent]
   ├──► [portfolio_agent]
   ├──► [news_agent]
   ├──► [document_agent]
   ├──► [thematic_agent]
   ├──► [causal_agent]
   └──► [performance_agent]
              │
              ▼
        [synthesis_node] ── enforces citation contract
              │
              ▼
           [END / stream]
```

Conditional edges are implemented as Python callables that inspect the `state["active_subagents"]` list. Multiple sub-agents can be activated in parallel for compound queries (LangGraph's `Send` primitive handles fan-out).

### 9.3 Memory & Checkpointing

- **MemorySaver** (in-process): stores state graph snapshots per `thread_id` (= `session_id`) enabling multi-turn conversation continuity within a session.
- **StoreBackend** (persistent): stores long-term memories across sessions — injected as context at the start of each new conversation. Backed by PostgreSQL.
- **CompositeBackend**: combines both, defined in `src/agents/memory.py`.

### 9.4 Streaming

LangGraph's `astream_events()` API emits token-level events. The FastAPI `/chat/query` endpoint converts these to Server-Sent Events (SSE) and streams them to the frontend. The frontend's Minerva Chat view renders markdown incrementally as tokens arrive.

---

## 10. Deep Agents — Why and How

### 10.1 Action Masking

In DeepAgents, each sub-agent is instantiated with an explicit `tools=[ ... ]` list. This list is the *only* tool manifest available to that agent during its planning loop — it cannot call tools outside this list regardless of what the LLM produces. This is qualitatively different from prompt-level instructions ("don't use tool X") which a sufficiently long reasoning chain can override.

### 10.2 Per-Agent Planning Loop

Each sub-agent runs a ReAct-style loop: Reason → Act (tool call) → Observe (tool result) → Reason again. The maximum number of steps is bounded by `DEEP_AGENT_MAX_STEPS` (environment variable, default 10). Loops that do not converge within the step budget return a partial result with a `TIMEOUT` flag rather than hanging.

### 10.3 Framework Comparison

| Criterion | Monolithic LLM | Single ReAct Agent | CrewAI | AutoGen | **Minerva (DeepAgents + LangGraph)** |
|---|---|---|---|---|---|
| Multi-step reasoning | Limited by context | Yes (single loop) | Yes | Yes | Yes, with explicit graph |
| Action masking | No | No | Partial (role config) | No | Yes (tool manifest per agent) |
| Stateful conversation | No | Manual | Manual | Manual | Native (MemorySaver) |
| Streaming support | Provider-dependent | Manual | Limited | Limited | Native (LangGraph events) |
| Parallel sub-agents | No | No | Yes (sequential default) | Yes | Yes (Send primitive) |
| Production maturity | High | Medium | Medium | Low | Medium–High |
| Data residency (local LLM) | No | Depends | Depends | No | Yes (Ollama path) |

---

## 11. LLM & Embedding Strategy

### 11.1 Provider Abstraction

All LLM calls go through one of two middleware wrappers:
- `backend-ai/src/agents/middleware_openai_compat.py` — wraps any OpenAI-compatible API (Ollama, DeepSeek, OpenAI). Handles timeout, retry, and streaming.
- `backend-ai/src/agents/middleware_groq.py` — Groq-specific wrapper exploiting LPU inference speed.

The active provider is selected via the `LLM_PROVIDER` environment variable at startup. The LangGraph graph is constructed once and is provider-agnostic.

### 11.2 Provider Table

| Provider | Model | Primary Use Case | Approx. Cost | Latency Profile | Key Trade-off |
|---|---|---|---|---|---|
| **Anthropic Claude** | claude-sonnet-4-6 | Deep reasoning, complex multi-hop queries | $$$ | 3–8 s | Best quality; highest cost |
| **Groq** | llama-3.3-70b-versatile | Latency-critical paths (intent classification, routing) | $ | < 1 s | Fast; context window smaller than Claude |
| **OpenAI** | gpt-4o-mini | Balanced reasoning + tool use | $$ | 2–5 s | Good fallback; data leaves India |
| **DeepSeek** | deepseek-chat | Cost-sensitive bulk operations | $ | 2–6 s | Low cost; occasional reasoning lapses |
| **Ollama (local)** | deepseek-r1:8b | Air-gapped / data-residency deployments | Free | 5–20 s (CPU) | No network call; GPU-dependent quality |

### 11.3 Embedding

Primary: `nomic-embed-text` 768-dim via Ollama (local, free). Fallback: OpenAI `text-embedding-3-small` 1536-dim (upcasting handled in `ETLLoadTask`). Qdrant collections are sized for the primary 768-dim space; the fallback path stores the OpenAI vector zero-padded to avoid re-indexing.

### 11.4 Gemini for ETL Enrichment

Gemini 2.5 Flash (`GEMINI_API_KEY`) is used exclusively in `src/services/gemini_enrichment_service.py` for batch ETL enrichment: generating company summaries, extracting structured metrics from prose, and flagging red flags. It is never called during interactive agent inference.

---

## 12. RAG Pipeline — End to End

### 12.1 Ingestion-Time Pipeline

```
PDF / DOCX / PPTX
       │  PyMuPDF + pdfplumber
       ▼
   Raw text + tables
       │  TextProcessor (src/etl/text_processor.py)
       ▼
  Cleaned, denoised text
       │  SemanticChunker (section-aware, 512T / 50T overlap)
       ▼
  Chunks + metadata
       │  EmbeddingGenerator (nomic-embed-text)
       ▼
  768-dim vectors
       │  ETLLoadTask (content-hash dedup)
       ▼
  Qdrant company_filings
```

### 12.2 Query-Time Pipeline

```
User query string
       │  Embed (same model as ingestion)
       ▼
  Query vector (768-dim)
       │  Qdrant filtered ANN search (top-k=8, filter by ticker if provided)
       ▼
  Top-k chunks + metadata
       │  Context window assembly (src/agents/tools/vector_search.py)
       ▼
  Prompt: [system] + [context chunks] + [user query] + [tool results]
       │  LLM call (provider from §11)
       ▼
  Draft answer with inline citations
       │  Citation enforcement node (synthesis_node in LangGraph)
       │  → Drops any claim without a source reference
       ▼
  Grounded answer + citation list
       │  SSE stream (FastAPI → frontend)
       ▼
  User sees answer with clickable citation chips
```

### 12.3 Latency Breakdown (p90)

| Step | Contribution |
|---|---|
| Query embedding (Ollama local) | ~150 ms |
| Qdrant ANN search (top-8) | ~20 ms |
| Context assembly | ~5 ms |
| LLM inference (Groq llama-3.3) | ~800 ms |
| LLM inference (Claude sonnet) | ~4,000 ms |
| Citation enforcement | ~50 ms |
| Redis cache check (hit path) | < 5 ms |
| **Total (Groq, cache miss)** | **~1.1 s** |
| **Total (Claude, cache miss)** | **~4.3 s** |

---

## 13. Causal Intelligence Engine

### 13.1 Overview

The Causal Intelligence Engine models geopolitical-to-commodity-to-sector-to-equity impact propagation. It is seeded at startup via `backend-ai/src/etl/seed_causal_data.py` and updated at runtime by the ETL event monitor. The **Causal Detective** sub-agent queries this engine at inference time.

### 13.2 Scope

- **11 causal chains** pre-defined and seeded.
- **19 sector exposures** mapping sectors to commodity sensitivities.

### 13.3 Example Chains

| Trigger Event | Commodity Link | Affected Sector | Mechanism | Impact Direction |
|---|---|---|---|---|
| Middle East conflict escalation | Crude oil prices rise | Aviation | Jet fuel is ~30% of airline opex | Negative (cost squeeze) |
| Middle East conflict escalation | Crude oil prices rise | Auto manufacturing | Petro-chemical input costs rise; petrochemical supply disruption | Negative |
| India raises ethanol-blending mandate (E20) | Ethanol demand increases | Sugar industry | Sugar mills divert cane to ethanol production; blending subsidy income | Positive |
| AI data-center buildout boom | Electricity demand rises | Power equipment & REITs | Data centers require GW-scale power; real estate for facility construction | Positive |
| AI data-center buildout boom | Silicon / specialty chemical demand | Industrial lubricants, coolants, spare parts | Cooling systems require thermal management fluids; hardware maintenance | Positive |
| Russia-Ukraine conflict | Natural gas price spike | Fertilizer industry | Nitrogen fertilizers derived from natural gas; input costs surge | Negative |

### 13.4 Detection Metric

Causal event detection F1 = **0.843** on a held-out historical geopolitical event benchmark (see §15). False negatives are more acceptable than false positives — the engine generates alerts only when confidence exceeds a configurable threshold.

---

## 14. Frontend Architecture

### 14.1 Views

| View | Feature Path | Backend Dependency |
|---|---|---|
| Dashboard | `features/dashboard/` | `/companies`, `/portfolios`, `/news` |
| Minerva Chat (IRIS) | `features/chat/` | `/chat/query` (SSE streaming) |
| Discovery | `features/discovery/` | `/companies/search`, `/screens/thematic` |
| Compare | `features/compare/` | `/compare/` (POST) |
| Portfolio | `features/portfolio/` | `/portfolios/{id}`, `/portfolios/{id}/metrics` |
| Domino Effect | `features/domino/` | `/causal/` |
| Company Workspace | `features/company/` | `/companies/{id}`, `/companies/{id}/financials` |
| Money / Financials | `features/money/` | `/companies/{id}/ratios` |
| Simulator | `features/simulator/` | `/simulator/` (CRUD) |
| Filings | `features/filings/` | `/companies/{id}/filings` |
| Timeline | `features/timeline/` | `/timeline/` |
| News | `features/news/` | `/news/` |
| Performance | `features/performance/` | `/portfolios/{id}/metrics` |
| Profile | `features/profile/` | `/users/{id}`, `/profiles/` |
| Settings | `features/settings/` | `/users/{id}` (PUT) |

### 14.2 API Client

All API calls are centralised in `frontend/src/shared/api/platform.ts`. Each function maps to one backend route with typed request/response shapes. No direct `fetch` calls in components.

### 14.3 State Management

React 19 hooks + Context API only — no Redux or Zustand. `useState` / `useEffect` / `useCallback` cover local UI state. `useContext` provides user identity (UUID stored in `localStorage`). The decision not to add Redux was deliberate: the app has no complex cross-component synchronisation requirements that justify the boilerplate.

### 14.4 Streaming Chat

The `/chat/query` endpoint returns `text/event-stream`. The Chat view uses the browser's `EventSource` API to consume SSE tokens incrementally. Markdown is rendered in real-time using `react-markdown` as tokens accumulate.

### 14.5 Type Safety

TypeScript strict mode is enabled. `npx tsc --noEmit` is run as part of every build. Current state: **0 type errors**. API response types are hand-maintained in `frontend/src/app/types.ts` and `frontend/src/shared/types/`.

---

## 15. Performance & Benchmarks

All metrics are from the project research paper, evaluated on a curated Indian equity benchmark dataset (NSE/BSE companies, 2022–2024 filings).

| Metric | Value | Evaluation Method |
|---|---|---|
| **Intent classification F1** (macro) | 0.943 | Prompt-based routing across 7 intent classes; held-out 500-query test set |
| **Retrieval MRR** (Mean Reciprocal Rank) | 0.89 | Financial document retrieval benchmark; ground-truth passages from analyst reports |
| **Causal event detection F1** | 0.843 | Historical geopolitical events mapped to sector impact; expert-labelled ground truth |
| **Expert evaluation score** | 4.21 / 5.0 | 3 experienced equity analysts; 60 randomly sampled responses; 5-point rubric |
| **Query latency p50** | ~2.5 s | End-to-end; Groq provider; production workload replay |
| **Query latency p90** | < 10 s | Includes complex multi-agent compound queries |
| **Cache hit response time** | < 5 ms | Redis hit on previously-computed SHA-256 keyed response |
| **Memory ceiling (60-min stress)** | 14.5 GB | Simulated 60-minute concurrent load; 16 GB cloud server budget |
| **Hallucination rate** | 0 % (evaluated) | All 60 expert-evaluated answers contained no ungrounded numerical claims |

---

## 16. Security & Compliance

### 16.1 API Key Management

All credentials are environment variables only — never committed to source control. `.env.example` ships with placeholder strings. The `.env` file is in `.gitignore`. In production, secrets should be moved to a vault (AWS Secrets Manager, HashiCorp Vault) — this is documented as a roadmap item.

### 16.2 Authentication

**Current state (demo):** a UUID is stored in `localStorage` and passed as a user identifier. There is no JWT issuance, no password hashing, and no session expiry.

**Planned:** `POST /auth/register` and `POST /auth/login` with bcrypt-hashed passwords, JWT access tokens (short-lived, 15 min), and refresh tokens (7-day, stored in `HttpOnly` cookie). Estimated implementation effort: ~4 hours. Deliberately deferred from the demo scope.

### 16.3 CORS

`ALLOWED_ORIGINS` environment variable controls the CORS allowlist. In production this should be restricted to the frontend origin only (e.g., `https://minerva.example.com`). Managed in `backend-ai/src/app/middleware.py`.

### 16.4 Data Residency

For deployments where financial data must not leave India (anticipated regulatory constraint), the system can run entirely on-premise:
- LLM → Ollama running `deepseek-r1:8b` locally (no external API calls).
- Embedding → Ollama `nomic-embed-text` locally.
- All databases → self-hosted via Docker Compose.
- External APIs (NSE, BSE) are Indian data — acceptable.
- FMP, Alpha Vantage, GDELT, news APIs would need Indian-hosted mirror or removal.

### 16.5 PII Handling

`users` table stores: name, email, a UUID, and optional Zerodha/Upstox broker link (API key stored as encrypted string in PostgreSQL, not in plaintext). Portfolio holdings are user-owned and isolated by `user_id` foreign key. No biometrics, no Aadhaar, no payment data.

---

## 17. Deployment Topology

### 17.1 Local Development (`docker-compose.yml`)

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | `postgres:15` | 5432 | Primary relational store |
| `redis` | `redis:7` | 6379 | Cache + Celery broker/result |
| `qdrant` | `qdrant/qdrant` | 6333 | Vector search |

Ollama runs natively on the host (not containerised) to enable GPU passthrough.

### 17.2 Process Map (local dev)

```
uvicorn src.main:app --port 8001 --reload    # FastAPI
celery -A src.celery_app worker              # Celery worker(s)
celery -A src.celery_app beat                # Celery Beat scheduler
ollama serve                                 # LLM + embedding inference
npm run dev (frontend/)                      # Vite dev server :5173
```

### 17.3 Migration Workflow

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

Initial seed: `python scripts/seed_db.py` (populates NSE/BSE universe, causal chain data, sample portfolio).

### 17.4 Health Check Endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | `{"status": "ok", "version": "1.0"}` |
| `GET /health` | Service + database connectivity status |
| `GET /api/v1/status` | Detailed subsystem status (DB, Redis, Qdrant, LLM provider) |

---

## 18. Anticipated Q&A — Defensive Reference

### Architecture & Design Choices

**Q1. Why a microservices-style separation instead of a monolithic backend?**
The ETL pipeline, the agent system, and the API layer have fundamentally different scaling requirements: ETL is batch and I/O-bound; the agent system is compute-bound and latency-sensitive; the API layer is request-response. Separating them allows each to be scaled independently (more Celery workers for ETL spikes, more API replicas for traffic spikes) without over-provisioning the others. The cost of this separation in a monorepo is low; the operational flexibility gained is significant.

**Q2. Why LangGraph over CrewAI or AutoGen?**
LangGraph gives us a typed state machine with explicit graph topology, native streaming via `astream_events`, and first-class checkpointing. CrewAI abstracts the graph away (useful for simpler pipelines, constraining for ours). AutoGen is a research framework not designed for production streaming. We combined LangGraph with DeepAgents specifically to get tool-manifest isolation at the sub-agent level, which neither CrewAI nor AutoGen provide out of the box.

**Q3. Why Qdrant over Pinecone or Weaviate?**
Qdrant is self-hostable, which is non-negotiable for data-residency compliance in an Indian regulatory context. Pinecone is SaaS-only (no on-premise option at time of development). Weaviate is heavier to operate and has a larger memory footprint. Qdrant also exposes filterable payload fields (ticker, doc_type), allowing compound vector + metadata queries in a single call, which simplifies the retrieval tool significantly.

**Q4. Why FastAPI over Django REST Framework?**
Django REST Framework carries the full Django ORM and middleware stack — appropriate when you need the admin panel, sessions, and templating. Minerva is an API-only service with no server-rendered pages. FastAPI's native async means LLM calls, database queries, and vector searches can all run concurrently on the same event loop without a thread pool. The automatic OpenAPI docs also reduced manual API documentation effort to zero.

**Q5. Why PostgreSQL instead of a purely document-based store like MongoDB for everything?**
About 70% of Minerva's data is inherently relational (companies → securities → filings → chunks; users → portfolios → holdings). SQL joins are more efficient and safer than application-level joins. MongoDB is used only for the profile store (truly document-shaped, schema-free, user-defined), where its flexibility is genuinely useful.

---

### AI / Agents

**Q6. How do you guarantee zero hallucination?**
"Zero hallucination" is a claim about the evaluated set, not a mathematical guarantee. The mechanism is a citation enforcement node in the LangGraph synthesis step: before an answer is returned, each numerical claim is checked for an associated source pointer (a `(chunk_id, page_number)` tuple or a `(table, row_id)` reference). Claims that fail this check are removed from the answer. On the 60-answer expert-evaluated set, no ungrounded claim passed the filter. In production, adversarial inputs or very unusual queries could still produce errors — this is documented as a limitation.

**Q7. What happens if the LLM provider is down?**
The `LLM_PROVIDER` env var can be changed at runtime without redeploying (Celery and FastAPI both read it at import time). The fallback chain in practice is: Claude → Groq → OpenAI → DeepSeek → Ollama (local). The Ollama path requires a GPU or a fast CPU; it is the "always-available" option because it has no external dependency. For the demo deployment, we run Groq as primary and Ollama as fallback.

**Q8. How do you prevent prompt injection attacks via user documents?**
User-uploaded documents are processed in an isolated pipeline (`src/etl/ingestion_service.py`) and stored in the `user_uploads` Qdrant collection. The RAG tool prefixes retrieved chunks with a system-level tag indicating they are user-provided content, not authoritative filings. The synthesis node is instructed to treat user-document content as unverified. We do not have a formal adversarial-injection test suite — this is flagged as a security gap for production hardening.

**Q9. What is the cost per query?**
For a typical compound query using Claude Sonnet-4-6: approximately 2,000 input tokens + 500 output tokens = ~$0.009 per query (at Anthropic's current pricing). With Groq llama-3.3-70b: ~$0.0005 per query. Cache hits cost nothing (Redis lookup). For a user making 20 queries per day, the monthly LLM cost on Groq is under ₹50.

**Q10. How does IRIS decide which sub-agents to invoke?**
The intent classifier node in LangGraph maps the user query to one or more of 7 intent classes (company analysis, comparison, portfolio, news, document, thematic, causal). This classification uses the LLM with a structured output schema (JSON with intent labels). The router then uses conditional edges to activate the matching sub-agents. For ambiguous or compound queries (e.g., "compare HDFC and ICICI and flag risks"), multiple agents are activated via LangGraph's `Send` primitive and run in parallel.

**Q11. Can the agents learn from user feedback?**
Not in the current version. The memory system stores conversation history and user-stated preferences (e.g., "I prefer conservative investments") as part of the StoreBackend, and IRIS injects these at the start of each session. However, there is no RLHF loop or fine-tuning pipeline. This is a roadmap item.

---

### Data & ETL

**Q12. How fresh is the financial data?**
Financial statements and ratios: refreshed twice daily (08:00 + 18:00 IST). NSE/BSE filings: crawled daily at 09:30 (NSE) and twice daily (BSE). News: every 6 hours. Live quotes (Upstox / Kite): on-demand at query time (not cached). Commodity prices: daily. Each data type has a `last_updated` timestamp and the staleness is surfaced to agents as part of tool output.

**Q13. What if NSE or BSE changes its filing format?**
The crawlers (`crawler_nse.py`, `crawler_bse.py`) are built against the current XML feed and portal structure. A format change would break the crawler. The `etl_runs` table logs failure states, so a broken crawl is immediately visible in monitoring. Mitigation: the crawlers use abstract `BaseCrawler` methods, so a format update requires only re-implementing the parsing logic without touching the downstream pipeline. This is a known maintenance risk.

**Q14. How do you handle financial tables inside PDFs?**
pdfplumber is used specifically for table extraction from PDFs (PyMuPDF handles text). Tables are converted to markdown pipe-table format before chunking so that row/column structure is preserved in the embedding. For heavily formatted multi-column PDFs, extraction quality degrades — this is a known limitation documented in the research paper.

**Q15. How large is the Qdrant vector index?**
For the demo dataset (approximately 200 companies, last 2 years of filings), the `company_filings` collection holds approximately 150,000 vectors at 768 dimensions. At 4 bytes per float, that's ~450 MB of raw vectors, plus HNSW graph overhead (~300 MB), totalling ~750 MB on disk. A full NSE universe (1,700+ companies, 5 years of filings) would scale to roughly 5–7 GB.

**Q16. Why FinBERT for news sentiment over a general BERT model?**
FinBERT was pre-trained on financial communication text (earnings reports, news, analyst notes). In internal testing on a sample of 500 Indian financial headlines, FinBERT achieved ~15% higher F1 on positive/negative/neutral classification compared to `bert-base-uncased`. The cost is a larger model size (439 MB vs. 110 MB).

---

### Scalability & Performance

**Q17. What is the primary bottleneck under high load?**
LLM inference time dominates for cache-miss queries. Under high concurrency, Qdrant ANN search and PostgreSQL remain fast (both handle thousands of QPS easily). The bottleneck is the LLM provider's rate limit or response latency. The Redis cache is the primary mitigation: identical queries (same SHA-256 hash) are served from cache in under 5 ms, so burst traffic from many users asking similar questions is handled without hitting the LLM.

**Q18. How do you scale Celery horizontally?**
Add more workers: `celery -A src.celery_app worker --concurrency=4`. Redis broker handles task distribution transparently. The only shared state is in PostgreSQL and Qdrant, which both support concurrent writes. Care must be taken with the batch enrichment task (batch_size=100 per run) to avoid two workers picking up overlapping company batches — this is managed by Celery's task locking pattern using Redis `SETNX`.

**Q19. What is the cold-start latency?**
First query after startup (no cached Ollama model, no Redis cache): ~8–15 seconds depending on LLM provider. Subsequent queries: 1–5 seconds. The Ollama model is loaded into VRAM on first call and stays warm. Redis warms up immediately. The FastAPI app has a lifespan hook that pre-warms the Qdrant client and database connection pool at startup (`backend-ai/src/app/lifespan.py`).

**Q20. Does the system handle concurrent multi-user sessions?**
Yes. Each session has a unique `session_id` which is the LangGraph `thread_id`. State is isolated per thread in MemorySaver. FastAPI's async request handling means multiple sessions run concurrently on the same event loop. The practical limit is LLM provider concurrency (typically 10–20 parallel requests per API key before rate limiting).

---

### Security & Ethics

**Q21. Is user portfolio data safe?**
Portfolio data is stored in PostgreSQL with a `user_id` foreign key. All API endpoints that access portfolios require the user's UUID in the request (currently; JWT enforcement is planned). The UUID is not publicly guessable but is not cryptographically strong — the JWT migration will fix this. No portfolio data is ever included in LLM prompts to external providers without explicit user consent.

**Q22. Can a user game the simulator to inflate scores?**
The simulator tracks XP, badges, and streaks but does not allow real-money flows — it is purely informational. There is no external leaderboard or monetisation tied to simulator scores, so gaming incentives are low. Trades are validated against live market prices at the time of submission (`simulated_trades.price_at_execution`), so a user cannot input a price they didn't actually execute at.

**Q23. Does Minerva give investment advice?**
No. Minerva is a research and information tool. Every response is accompanied by a disclaimer that it does not constitute financial advice and users should consult a SEBI-registered advisor before making investment decisions. The system is not registered with SEBI as an investment adviser.

**Q24. What are the risks of the AI's causal chain analysis being wrong?**
The causal engine has an F1 of 0.843, meaning approximately 16% of its detections are incorrect (false positives or false negatives). Users are shown the chain reasoning (Trigger → Commodity → Sector → Impact) and can inspect it. The system does not make buy/sell recommendations based on causal alerts — it only surfaces the chain for human review.

---

### Limitations & Future Work

**Q25. What does Minerva not do well today?**
Three known limitations: (1) PDF table extraction is imperfect for complex multi-column layouts — financial tables inside legacy BSE filings often parse poorly. (2) The system has no real-time streaming tick data — live quotes are on-demand, not pushed. (3) There is no portfolio rebalancing optimisation or mean-variance optimisation — the metrics engine computes descriptive statistics but does not suggest trades.

**Q26. What is on the technical roadmap?**
Priority items: JWT authentication (security); real-time WebSocket quote streaming (user experience); SEBI regulatory compliance review (legal); fine-tuning an embedding model on Indian financial text for higher retrieval precision; multi-language support (Hindi, Kannada) for broader accessibility; and a mobile-native React Native app.

**Q27. How would you productionise this beyond the demo?**
Key steps: (1) Replace Docker Compose with Kubernetes (HPA for Celery workers + FastAPI pods). (2) Move secrets to AWS Secrets Manager or equivalent. (3) Add a WAF in front of the FastAPI service. (4) Replace in-process MemorySaver with a distributed checkpoint store (e.g., Redis-backed). (5) Set up Prometheus + Grafana for LLM latency, cache hit rate, and ETL success rate monitoring. (6) Add a CI/CD pipeline (currently manual). (7) Obtain SEBI RAAS (Research Analyst Administration and Supervisory) registration if offering the platform publicly.

---

*Document generated 2026-06-02. For questions contact the project team at MSRIT CSE.*
