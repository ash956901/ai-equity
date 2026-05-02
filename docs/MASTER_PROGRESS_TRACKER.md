# Master Progress Tracker: AI-Native Equity Research OS

This document serves as the centralized, living progress tracker for the EquityAI platform. It is structured in execution order: **ETL → AI/Agentic → Backend → Frontend**.

**Overall Completion: ~65%**
> ETL + AI brains are fully done and verified (18/18 E2E tests pass). The remaining work is Backend REST APIs (Phase 3) and the Frontend UI (Phase 4).

---

## 🟢 PHASE 1: ETL Pipeline & Data Ingestion (100% Complete)
The backbone of the system. Converts raw financial documents into a structured, searchable, AI-ready knowledge base.

- [x] Web Crawlers (NSE/BSE async Celery task queues).
- [x] Document Parsing (pdfplumber for tables, PyMuPDF, DOCX, PPTX).
- [x] Semantic Text Cleaning & Normalization.
- [x] Contextual Semantic Chunking (with overlap).
- [x] Embedding Generation (Ollama `nomic-embed-text`).
- [x] Vector Storage (Qdrant) + Metadata Sync (PostgreSQL).
- [x] **Task 1.1: Financial Table Extraction**
  - *Goal:* Use pdfplumber to rip complex financial tables from Annual Reports into Markdown format.
  - *Verification:* `test_etl_pipeline.py` → Section "Table Extraction"
- [x] **Task 1.2: Proactive Metric Enrichment**
  - *Goal:* Extract structured metrics (Revenue, PAT, Debt, Capex) via LLM during ETL and save to the DB.
  - *Verification:* `test_e2e_full_flow.py` → Layer 1, test `1b: Metrics extraction` ✅
- [x] **Task 1.3: Automated Timeline Summarization**
  - *Goal:* Ingest step automatically triggers an LLM to generate a <50-word summary of the filing.
  - *Verification:* `test_e2e_full_flow.py` → Layer 1, test `1b: LLM Enrichment` ✅
- [x] **Task 1.4: Proactive Red Flag Extraction**
  - *Goal:* Scan incoming filings for governance/accounting red flags and save structured alerts to DB.
  - *Verification:* `test_e2e_full_flow.py` → Layer 1, test `1b: Red Flag extraction` ✅

---

## 🟢 PHASE 2: AI & Agentic Layer (100% Complete)
The intelligence brain — Iris and all specialist sub-agents. Fully verified.

- [x] LangGraph / DeepAgents Multi-Agent Orchestrator.
- [x] 6 Specialist Sub-agents: Company, Comparison, Portfolio, News, Doc Insight, **Thematic**.
- [x] Tool integrations: Vector Search, Financial API, Risk Detection, News.
- [x] Chat session management, persistence.
- [x] **Task 2.1: Thematic Discovery Engine (Global Search)**
  - *Goal:* Global vector search across all companies to find theme-matching stocks.
  - *Verification:* `test_e2e_full_flow.py` → Layer 2, tests `2b` ✅
- [x] **Task 2.2: Comparison Engine Refinement**
  - *Goal:* Comparison sub-agent outputs strict JSON for the frontend comparison table renderer.
  - *Verification:* `src/agents/prompts/comparison.py` → JSON schema enforced.
- [x] **Task 2.3: Quantitative Portfolio Intelligence**
  - *Goal:* Mathematical engines for Beta, Volatility, Sharpe Ratio, Diversification (HHI).
  - *Verification:* `test_e2e_full_flow.py` → Layer 4 (4a–4d) ✅
- [x] **Task 2.4: Agent Tool Error Handling & Retry Logic**
  - *Goal:* Agents get clean error messages (not crashes) when FMP or Qdrant fails.
  - *Verification:* `test_e2e_full_flow.py` → Layer 3, tests `3b`, `3d` ✅

**Full E2E Verification Command:**
```bash
cd backend-ai && .venv/bin/python test_e2e_full_flow.py
# Expected: 18/18 ✅ ALL LAYERS VERIFIED
```

---

## 🟠 PHASE 3: Backend APIs & Services (~20% Complete)
Exposing the intelligence to the client securely and efficiently.

- [x] `POST /chat/query` endpoint (Iris AI chat).
- [x] PostgreSQL database schemas (Users, Portfolios, Filings, Holdings).
- [x] Basic company routes (`/companies`, `/companies/{id}`).
- [ ] **Task 3.1: Timeline API**
  - *Goal:* `GET /timeline/{company_id}` returning the <50-word filing summaries from ETL enrichment.
  - *Priority:* HIGH — data already exists in DB, just needs a route.
- [ ] **Task 3.2: Portfolio & Workspace APIs**
  - *Goal:* Full CRUD for Portfolios/Holdings + `GET /portfolio/{id}/metrics` returning Beta, Sharpe, Volatility.
  - *Priority:* HIGH — math engine is done, just needs a route.
- [ ] **Task 3.3: Authentication & RBAC**
  - *Goal:* JWT auth with Retail vs Analyst roles.
  - *Priority:* MEDIUM — needed before frontend user flows.
- [ ] **Task 3.4: Streaming Responses (SSE)**
  - *Goal:* Upgrade `/chat/query` to Server-Sent Events so users see Iris "typing" in real-time.
  - *Priority:* MEDIUM — UX enhancement.
- [ ] **Task 3.5: Thematic Discovery API**
  - *Goal:* `GET /discovery/thematic?q=renewable+energy` calling the global vector search.
  - *Priority:* HIGH — connects Discovery Engine to frontend.
- [ ] **Task 3.6: Mock Market Data Integration**
  - *Goal:* Seed portfolio holdings with mock prices from Zerodha/Upstox (or static mock JSON) so the portfolio math engine has real input.
  - *Priority:* HIGH — required for portfolio dashboard demo.

---

## 🔴 PHASE 4: Frontend UI (React + Vite + Tailwind) (~10% Complete)
The final user-facing surface where the AI intelligence becomes visible.

- [x] Basic Vite + React 19 + TypeScript scaffolding.
- [x] Tailwind CSS v4 configured.
- [x] Basic routing structure.
- [ ] **Task 4.1: Authentication Screens**
  - *Goal:* Login / Registration UI connecting to JWT auth backend.
- [ ] **Task 4.2: Global Dashboard & Thematic Discovery View**
  - *Goal:* Hero search bar for semantic themes (e.g., "AI infrastructure stocks"), trending sector cards.
- [ ] **Task 4.3: Iris Chat Interface**
  - *Goal:* Streaming chat UI with markdown rendering, evidence citation links, and conversation history.
- [ ] **Task 4.4: Company Deep-Dive Workspace**
  - *Goal:* Financials, Ratios, Filing timeline, News, and Risk Flags all in one view.
- [ ] **Task 4.5: Comparison Table View**
  - *Goal:* Side-by-side rendering of the JSON comparison output from the Comparison sub-agent.
- [ ] **Task 4.6: Portfolio Dashboard**
  - *Goal:* Recharts visualizations for Beta, Sector Allocation, Sharpe Ratio, and Diversification Score.

---

## 📌 Key Architecture Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| LLM Provider | NVIDIA NIM (`gpt-oss-120b`) | Free, fast, OpenAI-compatible |
| Embedding | Ollama `nomic-embed-text` | Local, no cost, 768-dim |
| Vector DB | Qdrant | Fast, filterable, self-hosted |
| Agent Framework | DeepAgents + LangGraph | Multi-agent routing with tools |
| Market Data | FMP API (+ Zerodha mock) | Real pricing with fallback mock |
| PDF Parsing | pdfplumber | Best-in-class table extraction |

---

## 📎 Key Reference Documents

| Document | Purpose |
|---|---|
| `docs/E2E_STACK_VERIFICATION_GUIDE.md` | How to verify the full stack works |
| `docs/PROJECT_COMPLETION_STATUS.md` | Detailed module-by-module completion |
| `docs/FULL_ETL_AND_RAG_VERIFICATION.md` | ETL + RAG pipeline verification |
| `backend-ai/test_e2e_full_flow.py` | **The master verification script** |

---

*Last Updated: 2026-05-03 | Phase 1 ✅ + Phase 2 ✅ verified. Moving to Phase 3 Backend APIs.*
