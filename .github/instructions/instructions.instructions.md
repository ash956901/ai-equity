---
description: Always load these instructions for all files in this workspace — they define the project architecture, coding standards, and AI-specific constraints for the Equity Research Platform.
applyTo: '**'
---
# AI-Native Equity Research Platform: Copilot Instructions

## 1. Project Overview

This repository contains an **AI-Native Equity Research Platform** — a full-stack FinTech application that democratizes institutional-grade equity research for retail investors. It uses Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and Semantic Knowledge Graphs to synthesize unstructured financial data (PDFs, PPTs, concall transcripts, news feeds) into actionable intelligence.

### Core Capabilities
- **Multi-Dimensional Data Ingestion:** Automated scraping and parsing of NSE/BSE filings, investor presentations, concall transcripts, news, and board meeting decks.
- **N-th Order Thematic Discovery:** Maps "ripple effects" of news/events across interconnected industries using a Semantic Knowledge Graph (e.g., ethanol policy → petroleum sector → sugar industry).
- **"Iris" Deep Research Assistant:** A domain-specific conversational AI powered by Sarvam AI's sarvam-m model, grounded strictly in uploaded documents via an advanced RAG pipeline with strict context windowing.
- **Portfolio Intelligence & Automated Timeline:** Risk metrics (PE/PB, volatility), a scrolling feed of ≤50-word actionable insights from daily filings, and real-time WebSocket dashboards.

---

## 2. Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React (Vite, TypeScript), Tailwind CSS, React Router, assistant-ui, Recharts, WebSocket client |
| **Backend** | Python 3.10+, FastAPI, Pydantic v2, Uvicorn |
| **AI / ML** | Sarvam AI (sarvam-m), LangChain / LlamaIndex, Hugging Face Transformers (FinBERT), Llama 3 |
| **Databases** | PostgreSQL (relational), Pinecone (vector DB) |
| **Knowledge Graph** | NetworkX (in-memory graph logic) |
| **Scraping / Parsing** | BeautifulSoup, Selenium, pdfplumber, python-pptx, OCR (Tesseract) |
| **Quantitative** | Pandas, NumPy |
| **DevOps** | Docker, GitHub Actions CI, `.env` config |

---

## 3. Project Structure

```
/
├── frontend/             # Vite + React + TypeScript application
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   │   ├── assistant-ui/  # Chat thread components (assistant-ui primitives)
│   │   │   └── layout/        # Dashboard layout, sidebar
│   │   ├── pages/        # Route-level page components
│   │   ├── providers/    # React context providers (runtime, etc.)
│   │   ├── hooks/        # Custom React hooks
│   │   ├── lib/          # Utility functions, constants
│   │   └── types/        # Shared TypeScript interfaces & types
│   └── public/           # Static assets
│
├── backend/              # FastAPI server
│   ├── api/              # Route modules (routers)
│   ├── models/           # SQLAlchemy / Pydantic models
│   ├── services/         # Business logic layer
│   ├── db/               # Database connection, migrations (Alembic)
│   └── core/             # Config, security, middleware
│
├── ai_engine/            # AI & RAG subsystem
│   ├── rag/              # RAG pipeline (retriever, generator, reranker)
│   ├── prompts/          # LLM prompt templates (Jinja2 / string templates)
│   ├── embeddings/       # Embedding model wrappers & chunking strategies
│   ├── knowledge_graph/  # NetworkX graph builder & query logic
│   └── sentiment/        # FinBERT / LLM sentiment classification
│
├── data_pipeline/        # Scraping & ETL
│   ├── scrapers/         # Per-source scraping scripts (NSE, BSE, news, PPTs)
│   ├── parsers/          # Document parsing (PDF, PPTX, OCR)
│   └── etl/              # Transform, chunk, embed, and load into vector DB
│
├── tests/                # Mirrors source structure
│   ├── backend/
│   ├── ai_engine/
│   └── data_pipeline/
│
├── docs/                 # Architecture diagrams, API specs, evaluation reports
├── .github/              # CI workflows, Copilot instructions
├── .env.example          # Template for environment variables
└── docker-compose.yml    # Local development orchestration
```

---

## 4. Coding Guidelines

### 4.1 Python (Backend & AI Engine)

- **Formatting:** PEP 8 via `black` (line length 88) and `isort` for imports.
- **Type Hints:** Mandatory on all function signatures — parameters and return types (e.g., `def get_filing(ticker: str, year: int) -> FilingResponse:`).
- **Async First:** Use `async def` for all FastAPI routes, database calls (`asyncpg`), external API calls (LLM, Pinecone, scraping). Use `httpx.AsyncClient` over `requests`.
- **Pydantic Models:** Define request/response schemas with Pydantic v2 `BaseModel`. Use `Field(...)` with descriptions for documentation.
- **Error Handling:** Wrap external calls (LLM, DB, scraping) in `try/except` blocks. Return structured `HTTPException` responses with meaningful error codes. Never let the API crash on malformed financial data.
- **Logging:** Use `logging` module (not `print`). Log at appropriate levels — `info` for request flow, `warning` for fallback paths, `error` for caught exceptions.
- **Docstrings:** Google-style docstrings on all public functions and classes.

### 4.2 TypeScript / React (Frontend)

- **Components:** Always use functional components with React Hooks. No class components.
- **Typing:** Strictly type all props, state, and API response interfaces in `/frontend/types/`. Avoid `any`.
- **Styling:** Tailwind CSS utility classes only. No custom CSS files unless there is a compelling reason (e.g., complex animations). Use `cn()` helper (clsx + tailwind-merge) for conditional classes.
- **Chat UI:** Use `assistant-ui` primitives (`ThreadPrimitive`, `ComposerPrimitive`, `MessagePrimitive`, etc.) for the Iris chat interface. The runtime adapter connects to Sarvam AI's `sarvam-m` chat completions API.
- **Data Fetching:** Use React Query / SWR for server-state management. Keep API calls in `/frontend/src/lib/`.
- **File Naming:** `kebab-case` for files (e.g., `portfolio-card.tsx`), `PascalCase` for component exports.
- **Modularity:** Prefer small, composable components. Extract repeated patterns into reusable components or hooks.

### 4.3 API Design (FastAPI)

- RESTful conventions: `GET /api/v1/filings`, `POST /api/v1/iris/query`, etc.
- Version all endpoints under `/api/v1/`.
- Use dependency injection (`Depends(...)`) for DB sessions, auth, and shared services.
- All responses should follow a consistent envelope: `{ "data": ..., "meta": { ... } }` for collections, or direct Pydantic model serialization for single resources.

### 4.4 AI / RAG Specific

- **Prompt Templates:** Store all prompts as separate template files in `ai_engine/prompts/`. Never inline large prompts in Python code.
- **Chunking Strategy:** Document chunking must preserve semantic boundaries (e.g., by section/heading, not by arbitrary token count alone). Use overlapping chunks.
- **Retrieval:** Always include a relevance score threshold when retrieving from Pinecone. Discard low-confidence chunks rather than passing noise to the LLM.
- **Context Window:** Enforce strict context windowing for Iris queries — pass only retrieved document chunks, never the entire corpus.
- **Evaluation:** Track retrieval precision, answer faithfulness, and latency as first-class metrics. Target >90% factual retrieval accuracy.

### 4.5 Data Pipeline

- Each scraper should be idempotent — re-running it should not create duplicate records.
- Store raw scraped data before transformation so pipelines are reproducible.
- Log scraping failures with source URL and timestamp for retry.

---

## 5. Git & Workflow Conventions

- **Branch Naming:** `feature/<short-description>`, `fix/<short-description>`, `chore/<short-description>`.
- **Commits:** Conventional Commits format — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- **PRs:** Every PR should reference a task or issue. Include a brief description of *what* and *why*.

---

## 6. Testing

- Use `pytest` for all Python tests. Place tests in `/tests/` mirroring the source tree.
- Use `pytest-asyncio` for async route and service tests.
- Frontend tests with React Testing Library + Vitest/Jest.
- AI pipeline tests should include deterministic fixtures (known document chunks → expected retrieval results).

---

## 7. Boundaries & Constraints (CRITICAL)

- **Financial Accuracy:** The AI module must strictly adhere to provided document context (RAG). **Never** instruct the LLM to guess, extrapolate, or hallucinate financial metrics. If context is insufficient, the system must say so.
- **Security:** Never hardcode API keys, tokens, or credentials (Sarvam AI, Pinecone, PostgreSQL, etc.). Always use `.env` variables via `os.getenv()` / `pydantic-settings` (backend) or `import.meta.env` (Vite frontend). Ensure `.env` is in `.gitignore`.
- **Database Safety:** Do not write scripts that drop tables, truncate data, or alter PostgreSQL schemas without explicit user confirmation. Use Alembic migrations for all schema changes.
- **Dependencies:** Do not introduce heavy new dependencies without evaluating necessity. Prefer existing stack tools. If a new library is needed, note it clearly.
- **Cost Awareness:** LLM API calls (Sarvam AI) cost money. Implement caching for repeated queries and avoid unnecessary re-embedding of unchanged documents.
- **Data Privacy:** Scraped financial data may include sensitive corporate information. Do not log or expose raw document content in API error responses.