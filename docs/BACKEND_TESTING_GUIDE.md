# Backend → AI → ETL Pipeline: Testing & Verification Guide
**AI-Native Equity Research Platform (EquityAI)**

> This is the single authoritative guide for testing every layer of the backend stack — from the REST API surface down through the AI agent layer, all the way to the ETL pipeline that feeds the vector database.

---

## 🗺️ What You're Testing

```
HTTP Request (curl / frontend)
        ↓
  FastAPI REST API          ← /portfolios, /screens/thematic, /chat, /companies ...
        ↓
   Domain Service           ← PortfoliosService, ScreensService, ChatService ...
        ↓
   AI Agent (Iris)          ← DeepAgents + LangGraph orchestrator
        ↓
  Agent Tools               ← search_filings, thematic_discovery_search, calculate_ratios
        ↓
  VectorService             ← Qdrant semantic search (company_filings collection)
  + PortfolioService        ← Beta, Sharpe, Volatility math
        ↓
  ETL Layer                 ← ETLTransformTask → ETLLoadTask
        ↓
  Qdrant + PostgreSQL       ← Storage (vectors + metadata)
```

---

## Prerequisites

| Service | Port | Check Command |
|---|---|---|
| Ollama | `11434` | `curl http://localhost:11434/api/tags` |
| Qdrant | `6333` | `curl http://localhost:6333/collections` |
| PostgreSQL | `5432` | `psql -U postgres -c "\l"` |
| FastAPI backend | `8001` | `curl http://localhost:8001/health` |

**Start the backend:**
```bash
cd backend-ai
source .venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## SECTION 1 — ETL Pipeline (Raw Doc → Vector DB)

### Test 1A: Full Layered E2E Verification (Master Script)
**The quickest way to verify the entire ETL + AI stack in one command.**

```bash
cd backend-ai
source .venv/bin/activate
python test_e2e_full_flow.py
```

**Expected output: 18/18 ✅**
```
LAYER 1 — ETL Pipeline
  ✅ PASS  [1a: Company resolve]  UUID=43703f95-...
  ✅ PASS  [1b: LLM Enrichment]  Summary: Revenue up 20%...
  ✅ PASS  [1b: Red Flag extraction]  Flags: ['Market volatility', ...]
  ✅ PASS  [1b: Metrics extraction]  Metrics: {revenue_cr: 80000, ...}
  ✅ PASS  [1c: Semantic chunking]  3 chunks created
  ✅ PASS  [1d: Qdrant vector load]  Loaded 3 chunks into vector DB
  ...
  🎉 ALL LAYERS VERIFIED — Stack is production-ready!
```

---

### Test 1B: ETL Component Test (Text Parsing Only)
Tests the parser, cleaner, chunker, and embedder without Iris.

```bash
python test_etl_pipeline.py
```

**What it verifies:**
- `DocumentProcessor` parses TXT/PDF → raw text
- `TextCleaner` strips noise
- `SemanticChunker` creates overlapping contextual windows
- `OllamaEmbedder` returns 768-dim vectors

---

### Test 1C: Real PDF Extraction Test
Tests actual PDF parsing using `pdfplumber` (tables) and `PyMuPDF` (text).

```bash
python test_real_pdf_pipeline.py
```

**What it verifies:**
- Downloads a real PDF
- pdfplumber rips financial tables into Markdown format
- PyMuPDF extracts body text
- Full chunk generation with embeddings

---

### Test 1D: Verify Qdrant Data Directly
Confirm your ETL data landed in the vector DB.

```bash
python -c "
from src.services.vector_service import VectorService
svc = VectorService()
client = svc._get_client()
pts, _ = client.scroll(collection_name='company_filings', limit=2, with_payload=True)
for p in pts:
    print('Company:', p.payload.get('company'))
    print('Text:', p.payload.get('text', '')[:80])
    print()
"
```

---

### Test 1E: Celery Background Pipeline (Production Flow)
The real production ETL runs asynchronously when crawlers find new filings.

```bash
# Terminal 1 — start Celery worker
celery -A src.celery_app worker --loglevel=info

# Terminal 2 — trigger a task manually
python -c "
from src.etl.tasks import process_filing_task
process_filing_task.delay(
    file_path='uploads/filings/reliance_annual_report_e2e.txt',
    company_id='43703f95-b137-415b-b88b-5018a0883240',
    filing_id='test-filing-001',
    filing_type='Annual Report',
    company='Reliance Industries',
    year='2023'
)
print('Task dispatched — watch Celery worker logs')
"
```

**What to watch for in Celery logs:**
```
[INFO] ETLTransformTask: Processing filing...
[INFO] Generated 4 chunks with embeddings
[INFO] ETLLoadTask: Loaded 4 chunks into Qdrant
```

---

## SECTION 2 — REST API Endpoints (Backend Layer)

Run these after the backend server is up on `:8001`.

### Test 2A: Health & OpenAPI
```bash
# Health check
curl http://localhost:8001/health

# View all registered routes
curl -s http://localhost:8001/openapi.json | python3 -c "
import sys, json
paths = json.load(sys.stdin)['paths']
for path in sorted(paths):
    methods = list(paths[path].keys())
    print(f'  {str(methods):20}  {path}')
"
```

---

### Test 2B: Company Discovery & Search

```bash
# List companies (keyword search)
curl "http://localhost:8001/companies/?search=reliance&limit=5" | python3 -m json.tool

# Fast company search
curl "http://localhost:8001/companies/search?q=TCS" | python3 -m json.tool

# Company detail
curl "http://localhost:8001/companies/43703f95-b137-415b-b88b-5018a0883240" | python3 -m json.tool

# Company financials
curl "http://localhost:8001/companies/43703f95-b137-415b-b88b-5018a0883240/financials" | python3 -m json.tool

# Company ratios
curl "http://localhost:8001/companies/43703f95-b137-415b-b88b-5018a0883240/ratios" | python3 -m json.tool
```

---

### Test 2C: 🆕 Thematic AI Discovery (`GET /screens/thematic`)
**New endpoint — semantic AI stock discovery via Qdrant.**

```bash
# Find companies exposed to telecom regulatory risk
curl "http://localhost:8001/screens/thematic?q=telecom+regulatory+changes&limit=10" | python3 -m json.tool

# Find renewable energy plays
curl "http://localhost:8001/screens/thematic?q=renewable+energy+expansion&limit=10" | python3 -m json.tool

# Find AI infrastructure beneficiaries
curl "http://localhost:8001/screens/thematic?q=AI+data+center+infrastructure&limit=10" | python3 -m json.tool
```

**Expected response shape:**
```json
[
  {
    "company_id": "43703f95-...",
    "company_name": "Reliance Industries",
    "ticker_nse": "RELIANCE",
    "sector": "Refineries & Marketing",
    "relevance_score": 0.7172,
    "match_count": 8,
    "evidence_snippets": [
      "Risk Factors include... regulatory changes in the telecom sector."
    ]
  }
]
```

---

### Test 2D: Portfolio CRUD + 🆕 Risk Metrics (`GET /portfolios/{id}/metrics`)

```bash
# Step 1: Create a portfolio (needs valid user_id in DB)
curl -X POST "http://localhost:8001/portfolios/" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "<YOUR_USER_UUID>", "name": "My Portfolio", "is_primary": true}'

# Step 2: Add a holding
curl -X POST "http://localhost:8001/portfolios/<PORTFOLIO_ID>/holdings" \
  -H "Content-Type: application/json" \
  -d '{"company_id": "43703f95-b137-415b-b88b-5018a0883240", "quantity": 100, "average_price": 2800}'

# Step 3: Get full portfolio (includes metrics)
curl "http://localhost:8001/portfolios/<PORTFOLIO_ID>" | python3 -m json.tool

# Step 4: 🆕 Get ONLY risk metrics (for frontend charts)
curl "http://localhost:8001/portfolios/<PORTFOLIO_ID>/metrics" | python3 -m json.tool
```

**Expected /metrics response:**
```json
{
  "portfolio_id": "...",
  "portfolio_name": "My Portfolio",
  "total_value_inr": 280000.0,
  "portfolio_beta": 1.18,
  "sharpe_ratio": 0.33,
  "portfolio_volatility": 0.177,
  "diversification_score": 33,
  "sector_allocation": {
    "Refineries & Marketing": 1.0
  },
  "holdings": [...]
}
```

---

### Test 2E: Iris Chat (`POST /chat/query`)

```bash
# Basic company research query
curl -X POST "http://localhost:8001/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<YOUR_USER_UUID>",
    "query": "What are the key risk factors for Reliance Industries based on their recent filings?",
    "expertise_level": "intermediate"
  }' | python3 -m json.tool

# Thematic discovery via Iris
curl -X POST "http://localhost:8001/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<YOUR_USER_UUID>",
    "query": "Find me companies that are expanding into renewable energy",
    "expertise_level": "intermediate"
  }' | python3 -m json.tool

# Company comparison
curl -X POST "http://localhost:8001/compare/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<YOUR_USER_UUID>",
    "company_names": ["Reliance Industries", "Tata Consultancy Services"],
    "expertise_level": "intermediate"
  }' | python3 -m json.tool
```

---

### Test 2F: Timeline Feed

```bash
# Global timeline (all filings + news, last 90 days)
curl "http://localhost:8001/timeline/?limit=10" | python3 -m json.tool

# Company-specific timeline
curl "http://localhost:8001/timeline/?company_id=43703f95-b137-415b-b88b-5018a0883240&limit=10" | python3 -m json.tool
```

---

### Test 2G: Traditional Screen (SQL filter)

```bash
# Screen by sector
curl -X POST "http://localhost:8001/screens/run" \
  -H "Content-Type: application/json" \
  -d '{"sector": "Technology", "limit": 10}' | python3 -m json.tool
```

---

## SECTION 3 — AI & Agent Layer

### Test 3A: Vector Search Tools (Directly)
Test the LangChain tools that Iris uses, bypassing the full agent loop.

```bash
python -c "
from src.agents.tools.vector_search import search_filings, thematic_discovery_search

# Company-scoped search
result = search_filings.invoke({
    'company_id': 'Reliance Industries',
    'query': 'revenue growth debt reduction',
    'limit': 3
})
print('=== search_filings ===')
for r in result:
    print(f\"  Score: {r['score']:.3f} | {r['text'][:80]}\")

# Thematic global search
result2 = thematic_discovery_search.invoke({
    'query': 'telecom regulatory risk',
    'limit': 5
})
print('=== thematic_discovery_search ===')
for co in result2:
    print(f\"  {co['company_name']} | Score: {co['max_score']:.3f} | Matches: {co['match_count']}\")
"
```

---

### Test 3B: Portfolio Math Engine (Directly)
Test Beta, Sharpe, Volatility without needing an HTTP server.

```bash
python test_e2e_full_flow.py 2>/dev/null | grep "LAYER 4" -A 10
```

Or run directly:
```bash
python -c "
from src.services.portfolio_service import PortfolioService
from unittest.mock import MagicMock
from uuid import uuid4

mock_h = MagicMock()
mock_h.id = uuid4()
mock_h.company_id = uuid4()
mock_h.quantity = 100
mock_h.average_price = 2800.0
mock_h.current_price = 3100.0
mock_h.currency = 'INR'

mock_co = MagicMock()
mock_co.sector = 'Technology'

mock_db = MagicMock()
mock_db.query.return_value.filter.return_value.all.return_value = [mock_h]
mock_db.query.return_value.filter.return_value.first.return_value = mock_co

svc = PortfolioService(mock_db)
metrics = svc.calculate_metrics(uuid4())
print('Beta:', metrics['portfolio_beta'])
print('Sharpe:', metrics['sharpe_ratio'])
print('Volatility:', metrics['portfolio_volatility'])
print('Diversification Score:', metrics['diversification_score'])
print('Sector Allocation:', metrics['sector_allocation'])
"
```

---

### Test 3C: Error Resilience (Agent Tools)
Confirm that bad inputs don't crash the agent.

```bash
python -c "
from src.agents.tools.vector_search import search_filings
from src.agents.tools.financial import calculate_ratios

# Bad company name — should return clean error
result = search_filings.invoke({'company_id': 'NONEXISTENT_XYZ999', 'query': 'revenue'})
print('Bad company error:', result[0].get('error', 'NO ERROR RETURNED — BUG!'))

# FMP API miss — should return clean message
result2 = calculate_ratios.invoke({'company_id': 'Reliance Industries'})
print('FMP miss error:', result2.get('error', result2))
"
```

---

## SECTION 4 — Quick Smoke Test (All at Once)

Use this before every commit or deployment to verify nothing is broken:

```bash
cd backend-ai
source .venv/bin/activate

# 1. Run the full 18-check E2E test
python test_e2e_full_flow.py 2>/dev/null

# 2. Verify the server is up and new endpoints exist
curl -s http://localhost:8001/openapi.json | python3 -c "
import sys, json
paths = json.load(sys.stdin)['paths']
checks = ['/screens/thematic', '/portfolios/{portfolio_id}/metrics', '/chat/query', '/timeline/']
for c in checks:
    ok = c in paths
    print(f'  {\"✅\" if ok else \"❌\"}  {c}')
"

# 3. Verify Qdrant has data
python -c "
from src.services.vector_service import VectorService
svc = VectorService()
count = svc._get_client().count(collection_name='company_filings')
print(f'  Qdrant: {count.count} vectors in company_filings collection')
"
```

---

## What Each New Backend Endpoint Does

| Endpoint | What calls it | What it returns |
|---|---|---|
| `GET /screens/thematic?q=` | Frontend Discovery search bar | AI-matched companies with relevance score + filing evidence |
| `GET /portfolios/{id}/metrics` | Frontend Portfolio Dashboard | Beta, Sharpe, Volatility, Diversification, Sector Allocation |
| `POST /chat/query` | Frontend Iris Chat | AI research answer grounded in vector DB filings |
| `GET /timeline/` | Frontend Timeline feed | Chronological filings + news events |
| `POST /compare/` | Frontend Comparison workspace | JSON comparison matrix of two companies |

---

## Current Backend Status at a Glance

| Domain | Endpoints | Status |
|---|---|---|
| `/chat` | `POST /query`, `GET /sessions/{user_id}` | ✅ Live |
| `/companies` | list, search, detail, quote, financials, ratios, enrich | ✅ Live |
| `/portfolios` | CRUD + holdings + 🆕 `/metrics` | ✅ Live |
| `/screens` | run (SQL filter) + 🆕 `/thematic` (AI) | ✅ Live |
| `/compare` | `POST /` (AI comparison) | ✅ Live |
| `/timeline` | `GET /` (filings + news feed) | ✅ Live |
| `/users` | profile get/update, KYC | ✅ Live |
| `/alerts` | CRUD | ✅ Live |
| `/watchlists` | CRUD | ✅ Live |
| `/auth` | login / register | ❌ Not built yet |

---

## Troubleshooting Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| `connection refused` on `:8001` | FastAPI not started | Run `uvicorn src.main:app --port 8001` |
| `connection refused` on `:11434` | Ollama not running | Run `ollama serve` |
| `connection refused` on `:6333` | Qdrant not running | Run `docker start qdrant` or `qdrant` binary |
| `ForeignKeyViolation` on portfolio create | User UUID not in DB | Create user first via `/users/` or seed directly |
| Agent gives "unable to locate" | No data in Qdrant | Run `python test_e2e_full_flow.py` to seed data |
| `thematic_search` returns `[]` | Score threshold too high | Data exists but below 0.5 similarity — use a closer query |

---

*Last Updated: 2026-05-03 | Backend gaps closed: 2/3 | E2E: 18/18 ✅*
