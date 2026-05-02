# Full ETL & RAG Pipeline Verification Guide

> **Updated 2026-05-03** — ETL + RAG are both 100% complete and verified. The master verification script (`test_e2e_full_flow.py`) covers all 18 checks across 5 layers. See **`BACKEND_TESTING_GUIDE.md`** for the complete backend testing reference.

---

## The Complete Pipeline Flow

```
Raw Document
    ↓
ETLTransformTask     → parse → clean → chunk → embed → enrich (LLM)
    ↓
ETLLoadTask          → upsert chunks into Qdrant
    ↓
VectorService        → query_points() with company_id filter OR global thematic search
    ↓
Agent Tools          → search_filings / thematic_discovery_search (LangChain @tools)
    ↓
LangGraph DeepAgent  → route to correct sub-agent
    ↓
Iris (LLM)           → synthesize grounded answer from retrieved context
```

---

## Master Verification Command

```bash
cd backend-ai
source .venv/bin/activate
python test_e2e_full_flow.py
```

### What Each Layer Tests

| Layer | Tests | Checks |
|---|---|---|
| **Layer 1** — ETL Pipeline | Company resolve, LLM enrichment, chunking, Qdrant load | 6 checks |
| **Layer 2** — Vector / RAG | Company-scoped search, global thematic search, tool wrapper | 3 checks |
| **Layer 3** — Agent Tools | `search_filings`, `calculate_ratios`, `detect_risk_flags`, error handling | 4 checks |
| **Layer 4** — Portfolio Math | Beta, Sharpe, Volatility, Diversification | 4 checks |
| **Layer 5** — Iris Agent | Full agent response via LLM + vector retrieval | 1 check |

---

## Individual Test Scripts

| Script | Tests | When to Use |
|---|---|---|
| `test_e2e_full_flow.py` | All 5 layers, 18 checks | Before every commit |
| `test_etl_pipeline.py` | ETL components only (no Iris) | Debugging ETL |
| `test_real_pdf_pipeline.py` | Real PDF parsing | Debugging PDF extraction |
| `test_rag_pipeline.py` | ETL → Qdrant → Iris (older script) | Legacy, replaced by E2E |

---

## Verified Capabilities

### ETL (100% Complete)
- ✅ PDF text extraction (PyMuPDF)
- ✅ PDF table extraction (pdfplumber → Markdown)
- ✅ Semantic chunking with section detection (MD&A, Risk Factors, Financials)
- ✅ 768-dim embeddings (Ollama `nomic-embed-text`)
- ✅ Qdrant vector upsert with metadata (company_id, filing_id, section, year)
- ✅ LLM timeline summaries (<50 words per filing)
- ✅ LLM red flag extraction (structured alerts)
- ✅ LLM financial metric extraction (revenue, debt, capex in JSON)
- ✅ PostgreSQL metadata sync

### RAG / AI Layer (100% Complete)
- ✅ Company-scoped semantic search (`search_filings` tool)
- ✅ Global thematic discovery (`thematic_discovery_search` tool)
- ✅ 6 specialist sub-agents wired to tools
- ✅ Clean error handling (no crashes on bad input or empty DB)
- ✅ Portfolio math: Beta, Sharpe, Volatility, Diversification Score
- ✅ Iris responds to RAG queries with grounded, evidence-based answers

---

## Testing Specific Scenarios

### Scenario A: "Does Qdrant have data?"
```bash
python -c "
from src.services.vector_service import VectorService
svc = VectorService()
count = svc._get_client().count(collection_name='company_filings')
print('Total vectors:', count.count)
"
```

### Scenario B: "Does semantic search work?"
```bash
python -c "
from src.services.vector_service import VectorService
from uuid import UUID
svc = VectorService()
results = svc.search_company_filings(
    company_id=UUID('43703f95-b137-415b-b88b-5018a0883240'),
    query='revenue growth risk factors',
    limit=3
)
for r in results:
    print(f'Score: {r[\"score\"]:.3f} | {r[\"text\"][:100]}')
"
```

### Scenario C: "Does thematic discovery work?"
```bash
python -c "
from src.services.vector_service import VectorService
svc = VectorService()
results = svc.thematic_search('renewable energy expansion', limit=5)
for r in results:
    print(f'{r[\"company_name\"]} | Score: {r[\"max_score\"]:.3f} | Matches: {r[\"match_count\"]}')
"
```

### Scenario D: "Does Iris answer from filings?"
```bash
# Requires FastAPI server running on :8001
curl -X POST "http://localhost:8001/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "query": "What risk factors does Reliance Industries mention in their filings?",
    "expertise_level": "intermediate"
  }' | python3 -c "import sys, json; r = json.load(sys.stdin); print(r['response'][:400])"
```

---

## For Full Backend API Testing

See → **`docs/BACKEND_TESTING_GUIDE.md`**

*Last Updated: 2026-05-03 | ETL: 100% ✅ | RAG: 100% ✅ | New API endpoints: `/screens/thematic` + `/portfolios/{id}/metrics`*
