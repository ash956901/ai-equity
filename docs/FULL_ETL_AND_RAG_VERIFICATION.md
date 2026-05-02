# Full ETL & RAG Pipeline Verification Guide

This document outlines how to test and verify the **Full Semantic Financial ETL and RAG Pipeline**. This covers the complete lifecycle of financial documents—from ingestion and PDF extraction to semantic chunking, Qdrant vector storage, and finally LLM-based Retrieval-Augmented Generation (RAG) using Iris.

---

## 🟢 1. The Real PDF Extraction Test (ETL Transform)
This test proves that the system can successfully download an **actual PDF file**, use `PyMuPDF` (`fitz`) to extract text, and pass it through the semantic cleaner, chunker, and embedder.

**How to run it:**
```bash
cd backend-ai
source .venv/bin/activate
python3 test_real_pdf_pipeline.py
```

**What it does:**
1. Downloads a real PDF file to `uploads/filings/sample_report.pdf`.
2. Passes it to the `ETLTransformTask`.
3. The `DocumentProcessor` recognizes `.pdf`, uses `PyMuPDF` to rip the text natively.
4. Outputs the overlapping chunks embedded with `nomic-embed-text` vectors.

---

## 🟡 2. The End-to-End RAG Verification (ETL → VectorDB → Iris)
This test proves the pipeline's capability to orchestrate the entire lifecycle locally: ingesting data, pushing it into the vector database, and having the conversational AI Agent (Iris) query it dynamically.

**How to run it:**
```bash
cd backend-ai
source .venv/bin/activate
python3 test_rag_pipeline.py
```

**What it does:**
1. **Company Resolution:** Uses the `resolve_company` tool (connected to local DB / FMP API) to find the UUID for "Reliance Industries".
2. **Document Transform:** Rips a dummy "Annual Report", cleans it, and chunks it into semantic segments (like *Management Discussion*, *Risk Factors*).
3. **Load to Qdrant:** Takes the extracted chunks with 768-dimensional embeddings and performs a bulk upsert to your local `company_filings` Qdrant collection using the resolved `company_id`.
4. **Agent Inference:** Dispatches a user query to **Iris**: *"What are the key risk factors and revenue growth for Reliance Industries based on their recent filings?"*
5. **RAG Orchestration:** 
   - Iris invokes the `company-analysis` subagent.
   - The subagent invokes the `search_filings` vector retrieval tool.
   - The tool filters Qdrant by the `company_id` and pulls back the exact semantic chunks inserted seconds ago.
   - Iris synthesizes the financial data to answer the user query exactly as requested.

---

## 🔵 3. Background Celery Testing (Production Flow)
To ensure the pipeline works asynchronously during production:

1. Start all Docker containers (PostgreSQL, Qdrant, Redis).
2. Start the Celery worker in one terminal:
   ```bash
   cd backend-ai
   source .venv/bin/activate
   celery -A src.celery_app worker --loglevel=info
   ```
3. Trigger a crawler task (e.g., `crawl_nse_filings()`). 
4. **Observe:** You will see the Celery queue automatically detect the new filing, trigger `etl.process_filing`, extract the PDF/DOCX, and log a successful insertion into Qdrant.

---

## 🧠 Summary of System Capabilities 
- **Parser Supported Formats:** PDF (`pdfplumber` for text AND Markdown-formatted tables), DOCX (`python-docx`), PPTX (`python-pptx`), TXT.
- **LLM Enrichment:** Automatically extracts actionable Timeline Summaries, identifies Red Flags, and rips strict JSON financial metrics during ingestion.
- **Semantic Structuring:** Detects standard financial sections (Risk Factors, Financial Statements, MD&A) and performs overlapping paragraph-based chunking.
- **Embedder:** Defaults to local `ollama:nomic-embed-text` (configurable to OpenAI).
- **Vector DB:** Qdrant with custom payload matching.
- **Database Storage:** Saves vectors to Qdrant and saves the extracted summaries and metrics to PostgreSQL simultaneously.
- **Inference Agent:** LangGraph DeepAgent orchestrating 5 specialist subagents with progressive context retrieval.
