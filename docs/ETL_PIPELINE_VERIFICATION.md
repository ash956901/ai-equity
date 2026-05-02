# ETL Pipeline Verification Guide (Document Processing Stage)

This document provides a guide to verify the **Semantic Financial ETL Pipeline**, which transforms unstructured financial documents into structured, vectorized knowledge for the AI-Native Equity Research Platform.

## 1. Overview of Completed Stages

The Document Processing Stage encompasses the following implemented flow:
1. **EXTRACT (Ingestion Service)**: Downloads raw filings and stores metadata in PostgreSQL.
2. **TRANSFORM (Core Intelligence Layer)**:
    - **Parser**: Converts PDF, DOCX, PPTX, TXT into raw text.
    - **Cleaner**: Strips headers/footers, and normalizes currency & whitespace.
    - **Semantic Chunker**: Identifies major sections (e.g., "Management Discussion", "Risk Factors") and applies overlapping paragraph-based chunking.
    - **Embedder**: Generates 768-dimensional embeddings using `nomic-embed-text` via Ollama.
3. **LOAD (Storage Layer)**:
    - Automatically structures payloads to include metadata tags (`company_id`, `filing_id`, `filing_type`, `section`, `text`, `year`).
    - Upserts chunks into the `company_filings` Qdrant collection.

## 2. How to Verify the Pipeline

### Option 1: Run the Standalone Pipeline Test
We have created a dedicated test script `test_etl_pipeline.py` which mocks a document and runs it through the exact components.

```bash
cd backend-ai
source .venv/bin/activate
python3 test_etl_pipeline.py
```

**Expected Output:**
You should see output similar to the following, verifying that all stages completed without infinite loops or memory crashes:
```text
Testing ETL Pipeline...
Created test document at uploads/filings/test_doc.txt
Running Transform Task...
Generated 4 chunks.

Chunk 1:
  Text: Reliance Industries Limited
  Section: introduction_management_discussion_and_analysis
  Embedding size: 768
  Metadata tags: ...
...
Pipeline components instantiated and chunks generated successfully.
```

### Option 2: Verify End-to-End Celery Integration
The true ETL pipeline runs asynchronously in the background using Celery. When a new filing is crawled, a task is automatically dispatched.

1. **Start Qdrant, PostgreSQL, and Redis**: Ensure your local database stack is running via Docker.
2. **Start the Celery Worker**:
   ```bash
   cd backend-ai
   source .venv/bin/activate
   celery -A src.celery_app worker --loglevel=info
   ```
3. **Trigger a Crawl Task**:
   When a crawl finishes downloading a document (via `crawl_nse_filings`), watch the Celery worker logs. You should see it execute `etl.process_filing`, extract the document from `uploads/filings/`, generate embeddings, and log:
   `Loaded <N> chunks into Qdrant collection company_filings`.

### Option 3: Verify the Vector DB (Qdrant)
You can directly check if the data exists and is structured correctly inside Qdrant.

1. Open the Qdrant Web UI (usually accessible at `http://localhost:6333/dashboard`).
2. Select the `company_filings` collection.
3. Inspect a vector point payload. You should see:
   - Vector array of size 768.
   - Payload containing: `text`, `company_id`, `filing_id`, `filing_type`, `filing_date`, `document_type`, and `section`.

## 3. Next Steps: Connecting to RAG

Now that the ETL Document Pipeline is fully functional and storing high-quality semantic chunks into Qdrant, the next natural step is to query this data using the **Conversational AI Agent (Iris)**.

- **Vector Service**: The `VectorService` in `src/services/vector_service.py` is fully compatible and is already pointing to the `company_filings` collection using the stored `company_id` filters.
- **RAG Generation**: Feed the retrieved context directly into the Deep Agent / LangChain prompts to generate grounded, evidence-based financial insights.
