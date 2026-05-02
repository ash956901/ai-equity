# ETL Pipeline Verification Guide

> **Updated 2026-05-03** — ETL is 100% complete. This doc now points to the master test suite. For the full Backend + AI + ETL testing reference, see **`BACKEND_TESTING_GUIDE.md`**.

---

## Overview — What the ETL Pipeline Does

```
Raw Financial Document (PDF / DOCX / PPTX / TXT)
        ↓
  DocumentProcessor     → Extract raw text + tables
        ↓
  TextCleaner           → Strip headers, normalize currency/whitespace
        ↓
  SemanticChunker       → Detect sections (MD&A, Risk Factors, Financials)
                          Apply overlapping paragraph windows
        ↓
  OllamaEmbedder        → 768-dim vectors via nomic-embed-text
        ↓
  FilingEnricher (LLM)  → Extract: timeline summary, red flags, JSON metrics
        ↓
  ETLLoadTask           → Upsert chunks into Qdrant (company_filings)
                          Save enrichment data to PostgreSQL
```

---

## How to Verify (Quickest First)

### Option 1: Master E2E Test (Recommended)
Tests ETL **plus** every other layer in one shot.

```bash
cd backend-ai
source .venv/bin/activate
python test_e2e_full_flow.py
```

**Expected: 18/18 ✅ — Layer 1 checks all 6 ETL stages.**

---

### Option 2: Standalone ETL Script

```bash
python test_etl_pipeline.py
```

Tests the pipeline components (parser → cleaner → chunker → embedder) against a dummy document. No Iris involved.

---

### Option 3: Real PDF Test

```bash
python test_real_pdf_pipeline.py
```

Downloads an actual PDF and runs it through `pdfplumber` (tables) + `PyMuPDF` (text), proving the full document parsing capability.

---

### Option 4: Verify Qdrant Directly

```bash
python -c "
from src.services.vector_service import VectorService
svc = VectorService()
client = svc._get_client()
count = client.count(collection_name='company_filings')
print(f'Vectors in Qdrant: {count.count}')
pts, _ = client.scroll(collection_name='company_filings', limit=1, with_payload=True)
print('Sample payload:', pts[0].payload if pts else 'EMPTY')
"
```

---

### Option 5: Celery Background Worker (Production Mode)

```bash
# Terminal 1
celery -A src.celery_app worker --loglevel=info

# Terminal 2 — dispatch a filing task
python -c "
from src.etl.tasks import process_filing_task
process_filing_task.delay(
    file_path='uploads/filings/reliance_annual_report_e2e.txt',
    company_id='43703f95-b137-415b-b88b-5018a0883240',
    filing_id='test-001',
    filing_type='Annual Report',
    company='Reliance Industries',
    year='2023'
)
"
```

---

## Capabilities Confirmed ✅

| Capability | Verified Via |
|---|---|
| PDF text extraction (PyMuPDF) | `test_real_pdf_pipeline.py` |
| PDF table extraction (pdfplumber → Markdown) | `test_real_pdf_pipeline.py` |
| DOCX / PPTX parsing | `test_etl_pipeline.py` |
| Semantic chunking with section detection | `test_e2e_full_flow.py` Layer 1c |
| Embedding (Ollama `nomic-embed-text`, 768-dim) | All test scripts |
| Qdrant vector upsert | `test_e2e_full_flow.py` Layer 1d |
| LLM timeline summary generation | `test_e2e_full_flow.py` Layer 1b |
| LLM red flag extraction | `test_e2e_full_flow.py` Layer 1b |
| LLM financial metric extraction | `test_e2e_full_flow.py` Layer 1b |
| PostgreSQL metadata sync | `test_e2e_full_flow.py` Layer 1a |

---

## For Full Backend Testing

See → **`docs/BACKEND_TESTING_GUIDE.md`**

*Last Updated: 2026-05-03 | ETL Status: 100% Complete ✅*
