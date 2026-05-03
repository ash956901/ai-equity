---
name: equity-agent-architecture-refinement
overview: Refine the existing AI-native equity research platform design into a backend-only, agent-centric system optimized for Indian equities, heavy document/crawling workloads, and portfolio/comparison analysis, without frontend work for now.
todos:
  - id: design-core-data-model
    content: Design the Postgres schema for companies, financials, filings, news, portfolios, chats, and theme exposure with India-specific fields.
    status: completed
  - id: define-ingestion-pipelines
    content: Specify the crawling and ETL pipelines for NSE/BSE, investor relations sites, PDFs/PPTs, and news, including auto-discovery of investor URLs and idempotent runs.
    status: completed
  - id: select-and-integrate-vector-store
    content: Decide between a standalone vector DB or pgvector, then define how filings, presentations, and uploads are chunked, embedded, and queried per user/company.
    status: completed
  - id: langgraph-query-graph-design
    content: Refine the LangGraph query-time agent graph (router, analysis, comparison, portfolio, news, doc, synthesis) and the tools each node is allowed to call.
    status: completed
  - id: cloud-and-asynchronicity-strategy
    content: Choose target cloud (AWS/Azure), object storage, and background worker stack, and define how near-time queries interact with asynchronous ingestion jobs.
    status: completed
isProject: false
---

## Goal

Refine your current ChatGPT-designed architecture into a **backend-only, agent-centric research system** that:

- Focuses on **Indian stocks**, portfolio analysis, and company comparison
- **Crawls and ingests** filings and investor websites autonomously (no manual URLs)
- Processes **complex documents** (PDFs, PPTs with tables/graphics/charts)
- Uses **cloud storage + relational DB + vector search** where they add real value
- Supports **real-time-ish queries** with layman explanations tuned to user expertise.

## 1. Overall Architecture Adjustm

## ents

- **Drop frontend-for-now**: Keep FastAPI (or similar) as the only entrypoint; Next.js, Tailwind, Recharts move to a later phase.
- **Keep LangGraph as core orchestration**: Use it for deterministic graphs, but split into two main graphs:
  - **Ingestion Graph**: Crawler/ETL agents for NSE/BSE, investor sites, news.
  - **Query Graph**: Router → (CompanyAnalysis / Comparison / Portfolio / NewsSentiment / DocAnalysis) → Synthesis.
- **Reduce tech sprawl**: For an initial robust system, prefer:
  - **PostgreSQL** for all structured data (financials, portfolios, news metadata, chat sessions).
  - **One vector store** (Qdrant *or* pgvector in Postgres) for filings, investor docs, and user uploads.
  - **Redis** only if you really need fast session/memory caching; otherwise start with DB-backed sessions.

## 2. Data & Storage Design (Large Company Data, Cloud-Friendly)

- **Relational core in Postgres** (cloud-managed: AWS RDS / Azure Database for PostgreSQL):
  - `companies`, `exchanges`, `securities` (NSE/BSE mapping, ISIN, sector, industry, India-specific fields).
  - `financial_statements_raw` (normalized statements by company, period, source).
  - `financial_ratios` (derived metrics for fast queries; recomputed as needed).
  - `filings` and `filing_pages` (metadata + text pointers to object storage and/or vector index IDs).
  - `news_articles` with sentiment scores and links to company IDs.
  - `portfolios`, `holdings`, `portfolio_metrics`.
  - `chat_sessions`, `chat_messages`, `user_profiles` (with expertise level for layman vs expert tone).
- **Object storage in cloud** (AWS S3 / Azure Blob):
  - Store **raw PDFs, PPTs, images, and extracted chart images**; never in DB.
  - Maintain referential links from Postgres (`filings.raw_uri`, `uploads.raw_uri`).
- **Vector search**:
  - Use **one vector DB** for:
    - Parsed text chunks from filings, investor presentations, concalls.
    - Parsed text from news (optional at first).
    - User-uploaded docs in **per-user namespaces**.
  - This is necessary for flexible Q&A and hidden insight discovery; a pure keyword DB is not enough.

## 3. Crawling & ETL (Including Auto-Discovery of Investor Sites)

- **Source set** (India-first): NSE/BSE filings, company investor relations sections, press releases, concalls, annual reports, presentations.
- **Investor site auto-discovery**:
  - Maintain a `company_web_endpoints` table with patterns like `https://{domain}/investor`, `/investor-relations`, `/financials`.
  - Use a **discovery crawler** that, given the company domain (from manual mapping or basic search), probes common IR paths, parses sitemaps, and learns valid endpoints per company.
- **Crawling stack**:
  - **Scrapy** for large-scale text/HTML crawling (NSE/BSE, IR pages, RSS feeds).
  - **Playwright** only where JS-heavy rendering is required (keep this small due to overhead).
- **Document-focused ETL**:
  - **PDFs**: PyMuPDF or pdfplumber for text + table detection; `unstructured` or similar for robust layout-aware parsing; fallback OCR (Tesseract/Cloud Vision) for scanned docs.
  - **PPT/PPTX**: `python-pptx` to extract text, tables; export chart images to object storage, then run through a vision model.
  - **Charts/graphics**: cut out images → pass to a **vision-capable LLM** to reconstruct underlying series (e.g., "Revenue by segment", "Margin trend").
- **ETL orchestration**:
  - Use **background workers** (Celery/RQ/Arq) for crawling and parsing; FastAPI exposes control/status APIs but does not block.
  - Every pipeline run is **logged and idempotent** (keyed by `company_id`, `source`, `period`, `document_hash`).

## 4. Agent & Workflow Design (LangGraph) – Backend-Only

- **Separate ingestion vs query flows**:
  - Ingestion agents (scheduled/batch): `FilingCrawlerAgent`, `InvestorSiteCrawlerAgent`, `NewsIngestionAgent`, `DocParserAgent`, `EmbeddingAgent`.
  - Query-time agents (sync-ish):
    - `RouterAgent` (classify into analysis, comparison, portfolio, news, doc-upload follow-up).
    - `CompanyAnalysisAgent` (pulls financials/ratios, filings, embeddings as needed).
    - `ComparisonAgent` (multi-company, same headers: growth, margins, balance sheet, valuation, risk, business model).
    - `PortfolioAgent` (risk/exposure/overlap, simple scenario analysis first; advanced Monte Carlo later).
    - `NewsSentimentAgent` (summarizes latest India-related news, with impact on holdings).
    - `DocInsightAgent` (for one-off uploads, uses vector DB namespace + vision where needed).
    - `SynthesisAgent` (LLM-only; converts structured metrics + retrieved context into domain-aware, layman-tuned explanations).
- **Tooling boundaries**:
  - Tools handle **math, ratios, portfolio metrics, risk flags, screening and data access**.
  - LLM-based agents **never calculate**, only interpret and explain, as your planning instructions already state.
- **Memory**:
  - Short-term: conversation state per `chat_session_id` (in Postgres or Redis if you need speed).
  - Long-term: vector-backed memory for important user preferences and uploaded docs, with strict per-user namespaces.

## 5. Complex Document Understanding (Tables, Charts, Graphics)

- **Tables**:
  - Extract via pdfplumber/`unstructured` into **structured rows**; map known statement formats into normalized financial tables (line item mapping, unit normalization, currency, FY/quarter tagging).
  - For unstructured tables (e.g., segmental disclosures), store in a generic `statement_items` table plus embed the cleaned text in the vector store for semantic recall.
- **Diagrams/charts**:
  - Pipeline: detect → crop → store image → vision LLM → structured JSON like `{series_name, values, x_axis, unit}`.
  - Attach outputs back to the same `filing` or `presentation` document; allow both numeric querying (e.g., revenue by geography) and text Q&A.
- **Hidden insight layer**:
  - A periodic **offline agent** runs over each company’s embeddings and numeric metrics to:
    - Detect theme exposure (AI, defense, renewables, data centers, etc.).
    - Tag hidden subdomains and second-order exposures (e.g., coolant suppliers to data centers).
    - Store theme tags and impact scores in Postgres for fast filtering and discovery.

## 6. News & Sentiment for Indian Equities

- **Acquisition**:
  - Prefer **GNews**, NewsAPI, and/or Google News RSS queries filtered by `NSE:SYMBOL`, `BSE:SYMBOL`, and company names.
  - Normalize to `news_articles` table keyed to `company_id` where possible; allow orphan news with only ticker/text if mapping uncertain.
- **Sentiment**:
  - Start with **pretrained FinBERT / financial sentiment model** and add a small rules layer for India-specific events (SEBI orders, RBI policy, GST changes).
  - Store `sentiment_score`, `impact_level`, `relevance_to_company` and expose tools for agents to answer “why sentiment is bad/good now.”

## 7. Portfolio & Comparison Logic

- **Broker integration** (later in roadmap):
  - Abstract broker APIs behind a `BrokerService` so the core portfolio logic only sees normalized holdings and transactions.
  - For a student/early build, support **CSV uploads or manual holdings** first, then plug in Zerodha/Kotak/Groww.
- **Portfolio agent behaviour**:
  - Use tools to compute: sector/industry concentration, single-stock concentration, India vs global exposure, factor-style approximations (beta vs Nifty, large vs mid vs small caps).
  - Summaries must include both **technical view** and **"Explained Simply"** section per query.
- **Company comparison**:
  - Shared comparison template for 2–5 names with:
    - Growth, profitability, leverage, cash conversion.
    - Business model and moat summary.
    - Risk flags and macro sensitivity.
    - Clear layman-friendly conclusion (e.g., which is more stable vs more aggressive).

## 8. Real-Time-ish Queries & Performance

- **Near-time results**:
  - All heavy crawling/ETL work happens **asynchronously**; query graph only reads from prepared tables/embeddings.
  - For truly fresh filings, support a **"force refresh" tool call** that triggers an on-demand scrape for a single company, with progress status returned via polling or streaming.
- **Performance basics**:
  - Index Postgres on `(company_id, period)`, `(company_id, filing_date)`, and `(company_id, created_at)` for news.
  - Cache high-traffic aggregates (latest ratios, last 4 quarters summary) in Redis or materialized views.
  - Keep LangGraph nodes small and single-responsibility; long

