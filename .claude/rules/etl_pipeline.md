# Subsystem: ETL Pipeline

## Core Processing Flow (7 Stages)
1. **Raw Document** Ingestion
2. **DocumentProcessor**: Extracts text and tables (PDF/DOCX/PPTX, using PyMuPDF + pdfplumber).
3. **TextCleaner**: Cleans extractions.
4. **SemanticChunker**: Sections detection (MD&A, Risk Factors, Financials).
5. **OllamaEmbedder**: Converts to vectors using 768-dim `nomic-embed-text`.
6. **FilingEnricher**: LLM-powered extraction (timelines, red flags, metrics).
7. **Qdrant Loading**: Stored in `company_filings` collection.

## Verification & Testing
To verify changes made to the ETL flow, utilize these main scripts:
- `python test_e2e_full_flow.py`: Comprehensive test.
- `python test_etl_pipeline.py`: Component tests.
- `python test_real_pdf_pipeline.py`: Validation on real PDF processing.

## State
- Capable of PostgreSQL metadata sync with Qdrant operations.
- Driven via Celery worker background tasks.