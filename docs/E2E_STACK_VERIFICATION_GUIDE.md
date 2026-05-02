# E2E Stack Verification Guide
**AI-Native Equity Research Platform (EquityAI)**

> This document explains how to verify that the entire backend stack — from raw document ingestion to AI agent response — is working correctly before connecting to the backend REST APIs or the frontend UI.

---

## Prerequisites

Before running any test, ensure these services are running locally:

| Service | Port | Purpose |
|---|---|---|
| Ollama | `11434` | Embedding model (`nomic-embed-text`) |
| Qdrant | `6333` | Vector database |
| PostgreSQL | `5432` | Metadata & financial data |
| Redis | `6379` | Celery broker (optional for ETL) |

**Check services are live:**
```bash
curl http://localhost:11434/api/tags        # Should list nomic-embed-text
curl http://localhost:6333/collections     # Should list company_filings
```

---

## Run the Full E2E Test (One Command)

```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai

# Activate virtual environment
source .venv/bin/activate

# Run the comprehensive layer-by-layer verification
python test_e2e_full_flow.py
```

**Expected output (18/18 passed):**
```
============================================================
  LAYER 1 — ETL Pipeline
============================================================
  ✅ PASS  [1a: Company resolve]  UUID=43703f95-...
  ✅ PASS  [1b: LLM Enrichment]  Summary: Revenue up 20%...
  ✅ PASS  [1b: Red Flag extraction]  Flags: ['Market volatility', ...]
  ✅ PASS  [1b: Metrics extraction]  Metrics: {revenue_cr: 80000, ...}
  ✅ PASS  [1c: Semantic chunking]  3 chunks created
  ✅ PASS  [1d: Qdrant vector load]  Loaded 3 chunks into vector DB

============================================================
  LAYER 2 — Vector / RAG Layer
============================================================
  ✅ PASS  [2a: Company-scoped vector search]  Score=0.750 ...
  ✅ PASS  [2b: Global thematic vector search]  Top: Reliance Industries
  ✅ PASS  [2b: thematic_discovery_search tool]  Returned 1 companies

============================================================
  LAYER 3 — Agent Tools Layer
============================================================
  ✅ PASS  [3a: search_filings tool]  Score=0.632 ...
  ✅ PASS  [3b: calculate_ratios tool (error path)]  Clean error returned
  ✅ PASS  [3c: detect_risk_flags tool]  Returned 0 flags
  ✅ PASS  [3d: Error resilience (bad company)]  Clean error message

============================================================
  LAYER 4 — Portfolio Math Engine
============================================================
  ✅ PASS  [4a: Portfolio metrics computed]  Beta=1.18 | Sharpe=0.33
  ✅ PASS  [4b: Beta in realistic range (0-3)]
  ✅ PASS  [4c: Sharpe ratio positive]
  ✅ PASS  [4d: Diversification score 0-100]  Score=33

============================================================
  LAYER 5 — Iris Agent (Targeted RAG Query)
============================================================
  ✅ PASS  [5a: Iris agent responds to RAG query]  Tokens=7432

============================================================
  FINAL SUMMARY
============================================================
  Total: 18  |  ✅ Passed: 18  |  ❌ Failed: 0
  🎉 ALL LAYERS VERIFIED — Stack is production-ready!
```

---

## What Each Layer Tests

### Layer 1 — ETL Pipeline
Tests the full data ingestion pipeline — from raw text file to enriched, embedded chunks stored in Qdrant.

| Sub-test | What it verifies |
|---|---|
| `1a` Company Resolve | The DB can look up "Reliance Industries" and return a UUID |
| `1b` LLM Enrichment | Ollama/NVIDIA LLM reads the text and extracts a timeline summary, red flags, and financial metrics |
| `1b` Red Flags | The FilingEnricher correctly identifies governance/risk signals |
| `1b` Metrics | Structured JSON metrics are ripped from raw text (revenue, capex, debt) |
| `1c` Chunking | The text is split into semantic overlapping chunks correctly |
| `1d` Qdrant Load | All chunks are embedded and stored in the vector DB |

---

### Layer 2 — Vector / RAG Layer
Tests the intelligence retrieval system — both scoped (single company) and global (all companies).

| Sub-test | What it verifies |
|---|---|
| `2a` Company search | Searching within one company's filings returns relevant chunks with high semantic scores |
| `2b` Thematic global | A global query finds companies by theme without knowing their company_id |
| `2b` Tool wrapper | The LangChain tool `thematic_discovery_search` is callable and returns structured data |

---

### Layer 3 — Agent Tools
Tests that the LangChain tool wrappers work correctly, including failure paths.

| Sub-test | What it verifies |
|---|---|
| `3a` search_filings | The agent can search filings by company name (not just UUID) |
| `3b` calculate_ratios | When FMP API has no data, returns a *clean structured error* (not a crash) |
| `3c` detect_risk_flags | Returns empty list cleanly when no financial data is present |
| `3d` Bad company | An unknown company name returns a helpful error message to the agent |

---

### Layer 4 — Portfolio Math Engine
Tests the quantitative finance algorithms.

| Sub-test | What it verifies |
|---|---|
| `4a` All metrics present | Beta, Sharpe, Volatility, Diversification all computed |
| `4b` Beta range | Beta is between 0 and 3 (realistic market values) |
| `4c` Sharpe positive | Positive Sharpe means risk-adjusted return is positive |
| `4d` Diversification | Score is on a 0–100 scale (HHI-based sector concentration) |

---

### Layer 5 — Iris Agent
Tests the full AI agent pipeline — LLM reasoning over retrieved vector data.

| Sub-test | What it verifies |
|---|---|
| `5a` Agent responds | Iris makes tool calls, hits Qdrant, hits NVIDIA LLM, returns a real answer |

---

## Running Individual Layer Tests

If you need to debug a specific layer:

```bash
# Test only ETL + Vector (Layers 1 & 2)
python test_etl_pipeline.py

# Test the full pipeline that was used during ETL development
python test_real_pdf_pipeline.py

# Run the full E2E verification (all 5 layers)
python test_e2e_full_flow.py
```

---

## What "Production Ready" Means for This Stack

When all 18 tests pass, the following contract holds:

1. **You can ingest any financial PDF/text** → ETL will extract, chunk, embed, and enrich it automatically.
2. **You can search semantically** → Qdrant returns relevant chunks for any natural language query.
3. **Thematic discovery works globally** → Cross-company theme search is live (e.g. "telecom regulatory risk").
4. **Iris (the AI agent) works end-to-end** → It can route, call tools, and return grounded answers.
5. **Portfolio math is available** → Beta, Sharpe, Volatility, Diversification are all computed correctly.
6. **Errors are handled gracefully** → No layer crashes on bad input; clean error messages propagate.

This means **the ETL and AI layer are fully ready to be consumed by backend REST APIs and the frontend UI.**

---

## Connecting to Backend APIs (Next Step)

Once verified, the backend APIs that consume these layers are:

| API Endpoint | Layer It Uses |
|---|---|
| `POST /chat/query` | Layer 5 — Iris Agent |
| `GET /filings/search` | Layer 2 — Vector Search |
| `GET /discovery/thematic` | Layer 2 — Global Thematic Search |
| `GET /portfolio/{id}/metrics` | Layer 4 — Portfolio Math |
| `GET /timeline/{company_id}` | Layer 1 — ETL Enrichment |
| `GET /companies/{id}/flags` | Layer 3 — Risk Flag Tool |

---

*Last verified: 2026-05-03 | All 18/18 checks passed | Stack: Ollama (nomic-embed-text) + Qdrant + NVIDIA NIM LLM + PostgreSQL*
