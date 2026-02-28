# AI Equity Research Platform – Architecture Refinement Summary

## Overview

This document provides a comprehensive summary of the refined backend-only, agent-centric architecture for the AI-native equity research platform, optimized for Indian equities with focus on autonomous data ingestion, complex document processing, portfolio analysis, and intelligent insights.

---

## Key Design Decisions

### 1. **Backend-Only Architecture (No Frontend for MVP)**

- **API Layer**: FastAPI as the sole entry point
- **Focus**: Core intelligence, data pipelines, and agent reasoning
- **Future**: Frontend (Next.js) can be added later without architectural changes

### 2. **LangGraph for Agent Orchestration**

- **Choice**: LangGraph over CrewAI
- **Reason**: Deterministic state machines, better for production, explicit control flow
- **Architecture**: Two separate graphs:
  - **Ingestion Graph**: Crawler → Parser → Embedder → Theme Tagger
  - **Query Graph**: Router → Specialized Agents → Synthesis

### 3. **Data Stack Simplification**

- **PostgreSQL**: Single source of truth for all structured data
- **Qdrant**: Standalone vector DB for semantic search (chosen over pgvector for scale)
- **Redis**: Optional caching layer (start without it if budget-constrained)
- **S3**: Object storage for all raw documents, parsed JSON, and chart images

### 4. **Cloud Provider: AWS**

- **Reason**: Mature ecosystem, S3 dominance, cost-effective, student credits
- **Services**: ECS Fargate, RDS PostgreSQL, ElastiCache Redis, S3, SQS, EventBridge
- **Cost**: ~$400-500/month for MVP scale

### 5. **Asynchronous Processing with Celery + SQS**

- **Background workers** for all heavy lifting (crawling, parsing, embedding)
- **Query-time agents** read from pre-computed tables and vector DB
- **On-demand refresh** API for users who need latest data immediately

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User / Client                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST / WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  - Query routing                                                 │
│  - Authentication                                                │
│  - API endpoints                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  LangGraph   │    │  Background  │    │   Scheduled  │
│ Query Agents │    │   Workers    │    │     Jobs     │
│              │    │  (Celery)    │    │ (EventBridge)│
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       └───────────────────┴────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Qdrant    │  │      S3      │
│  (Financials,│  │   (Vector    │  │  (Raw docs,  │
│   Portfolio, │  │    Search)   │  │   Charts)    │
│   Chat, etc.)│  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Core Components

### 1. Database Schema (PostgreSQL)

**Key Tables:**

- **Companies & Securities**: `companies`, `exchanges`, `securities`, `indices`, `index_constituents`
- **Financial Data**: `financial_statements_raw`, `financial_ratios`, `statement_items`, `chart_series`
- **Documents**: `filings`, `filing_pages`, `company_web_endpoints`
- **Discovery**: `company_themes` (AI, defense, data centers, etc.)
- **News**: `news_articles` (with sentiment analysis)
- **Portfolio**: `users`, `portfolios`, `holdings`, `transactions`, `portfolio_metrics`
- **Chat**: `chat_sessions`, `chat_messages`, `user_uploads`
- **System**: `etl_runs`, `system_config`

**Design Principles:**

- Normalized financial data (store raw, compute ratios on-demand or cache)
- India-first (NSE/BSE tickers, INR currency, Indian sectors)
- UUID primary keys for cloud-friendliness
- Comprehensive indexing for fast queries

**Document**: [`01_database_schema.md`](./01_database_schema.md)

---

### 2. Ingestion & ETL Pipelines

**Autonomous Data Sources:**

1. **NSE/BSE Filings**: Daily crawl of regulatory filings
2. **Investor Relations Sites**: Auto-discovery of IR pages via sitemap parsing and heuristics
3. **News**: Hourly fetch from GNews, NewsAPI, Google News RSS
4. **Documents**: PDF/PPT parsing with table extraction and chart analysis via vision models

**Pipeline Architecture:**

```
Scheduler → Crawler → Document Parser → Table/Chart Extractor
                                     → Embedding Generator
                                     → Theme Tagger (offline)
```

**Key Features:**

- **Idempotent**: Hash-based deduplication prevents duplicate ingestion
- **Resilient**: Retry logic, partial success handling
- **Scalable**: Separate worker pools for I/O, CPU, and API-heavy tasks
- **Observable**: All runs logged to `etl_runs` table

**Document**: [`02_ingestion_pipelines.md`](./02_ingestion_pipelines.md)

---

### 3. Vector Store Strategy (Qdrant)

**Decision**: Qdrant (standalone) over pgvector

**Collections:**

1. **`company_filings`**: Parsed text from all regulatory filings, presentations, concalls
2. **`news_articles`**: News embeddings with sentiment metadata
3. **`user_uploads`**: User-uploaded documents with strict per-user namespaces

**Chunking Strategy:**

- **Size**: 500-1000 tokens per chunk
- **Overlap**: 100-150 tokens
- **Metadata**: Every chunk carries full context (company_id, filing_type, date, page)

**Embedding Model**: OpenAI `text-embedding-3-small` (1536 dimensions)

**Query Patterns:**

- Company-specific semantic search
- Multi-company comparison search
- Temporal analysis (how commentary changed over time)
- News sentiment search
- User upload search (namespace-isolated)
- Hybrid search (vector + keyword)

**Document**: [`03_vector_store_strategy.md`](./03_vector_store_strategy.md)

---

### 4. LangGraph Agent Design

**State Model**: Strongly-typed `ResearchState` with Pydantic

**Query Graph Flow:**

```
User Query
    ↓
Router Node (classify intent, extract entities)
    ↓
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  Company    │ Comparison  │  Portfolio  │    News     │
│  Analysis   │    Agent    │    Agent    │  Sentiment  │
└─────────────┴─────────────┴─────────────┴─────────────┘
    ↓
Synthesis Node (LLM-based reasoning + layman explanation)
    ↓
Final Response
```

**Agent Responsibilities:**

- **Router**: Classify query mode, extract company names/tickers, resolve to IDs
- **Company Analysis**: Fetch financials, ratios, filings, news, themes; detect risk flags
- **Comparison**: Compare 2-5 companies across growth, profitability, leverage, valuation, risk
- **Portfolio**: Analyze holdings, concentration, sector allocation, risk flags in portfolio
- **News Sentiment**: Semantic search over news, aggregate sentiment, identify themes
- **Doc Insight**: Analyze user-uploaded documents with vector search
- **Synthesis**: Generate domain-aware response with "Explained Simply" section

**Tool Separation:**

- **Tools** (non-LLM): All math, ratios, portfolio metrics, risk detection, data access
- **LLM Agents**: Interpretation, reasoning, synthesis, explanation

**Document**: [`04_langgraph_agent_design.md`](./04_langgraph_agent_design.md)

---

### 5. Cloud Deployment (AWS)

**Compute:**

- **API**: ECS Fargate (2 tasks, auto-scaling)
- **Workers**: ECS Fargate or EC2 Spot Instances (cost-optimized)

**Data:**

- **PostgreSQL**: RDS (db.t3.medium, Multi-AZ)
- **Redis**: ElastiCache (cache.t3.medium, 1 replica)
- **S3**: Object storage with lifecycle policies (archive to Glacier after 90 days)
- **Qdrant**: Self-hosted on EC2 (t3.large) with daily snapshots to S3

**Asynchronous Processing:**

- **Celery** with **SQS** as message broker
- Separate queues: `crawlers`, `parsers`, `embeddings`, `news`
- Auto-scaling based on queue depth

**Scheduled Jobs:**

- **EventBridge** (CloudWatch Events) for cron jobs
- Daily NSE/BSE crawls, hourly news fetch, weekly IR crawls, weekly theme tagging

**Near-Time Queries:**

- **Pre-computed tables**: `financial_ratios`, `portfolio_metrics`, `company_themes`
- **Redis caching**: 5-minute TTL for frequent queries
- **On-demand refresh**: API to trigger immediate company data refresh with task status polling
- **WebSocket streaming**: Real-time agent graph execution updates

**Monitoring:**

- **CloudWatch**: Logs, metrics, alarms
- **X-Ray**: Distributed tracing
- **Alarms**: High latency, high error rate, high queue depth, database CPU

**Cost**: ~$400-500/month for MVP scale

**Document**: [`05_cloud_deployment_strategy.md`](./05_cloud_deployment_strategy.md)

---

## Key Features & Differentiators

### 1. **Autonomous Discovery**

- Automatically discovers and crawls company investor relations pages
- No manual URL input required
- Learns from sitemap.xml and common IR path patterns

### 2. **Complex Document Understanding**

- **Tables**: Extract and normalize financial statements (P&L, BS, CF)
- **Charts**: Vision LLM extracts structured data from pie charts, bar graphs, line charts
- **Mixed documents**: Handle PDFs and PPTs with tables, charts, and text

### 3. **Hidden Insights & Theme Detection**

- Offline agent detects hidden subdomain exposure (e.g., Castrol → data center coolants)
- Theme tagging: AI, defense, renewables, EV, blockchain, etc.
- Second-order effects reasoning (e.g., rising steel prices → auto OEM margins improve)

### 4. **India-First Design**

- NSE/BSE ticker support
- Indian sector/industry classifications
- INR currency, Cr/Lakh units
- RBI policy, SEBI regulations, Union Budget as macro inputs
- Sentiment analysis tuned for Indian market events

### 5. **Portfolio Intelligence**

- Broker integration (Zerodha, Kotak, Groww) via abstracted service
- Concentration risk analysis (Herfindahl index)
- Sector allocation, beta vs Nifty
- Red flag detection across holdings

### 6. **Layman-Mode Explanations**

- User expertise level (beginner/intermediate/advanced) stored in profile
- Synthesis agent adapts explanation depth
- Always includes "Explained Simply" section for non-advanced users

### 7. **Real-Time News Sentiment**

- Hourly news fetch for portfolio companies
- FinBERT-based sentiment analysis
- Impact classification (High/Medium/Low)
- Affected dimension tagging (earnings, regulation, management, macro)

---

## Technology Stack

### Backend

- **Python 3.11**
- **FastAPI** (async web framework)
- **LangGraph** (agent orchestration)
- **Pydantic v2** (data validation)
- **SQLAlchemy** (ORM)
- **Alembic** (database migrations)

### Data

- **PostgreSQL 15** (relational database)
- **Qdrant** (vector database)
- **Redis** (caching)
- **AWS S3** (object storage)

### Crawling & Parsing

- **Scrapy** (web crawling)
- **Playwright** (JS-heavy sites)
- **PyMuPDF / pdfplumber** (PDF parsing)
- **python-pptx** (PPT parsing)
- **Tesseract** (OCR fallback)

### ML & AI

- **OpenAI GPT-4o** (reasoning, synthesis)
- **OpenAI text-embedding-3-small** (embeddings)
- **FinBERT** (sentiment analysis)
- **Vision LLM** (chart extraction)

### Infrastructure

- **AWS ECS Fargate** (containers)
- **AWS RDS** (managed PostgreSQL)
- **AWS ElastiCache** (managed Redis)
- **AWS S3** (object storage)
- **AWS SQS** (message queue)
- **AWS EventBridge** (scheduled jobs)
- **Celery** (background workers)

### Monitoring

- **CloudWatch** (logs, metrics, alarms)
- **AWS X-Ray** (distributed tracing)
- **Structlog** (structured logging)

---

## Implementation Roadmap

### Phase 1: Core Data Infrastructure (Weeks 1-2)

- [ ] Set up AWS account and base infrastructure (VPC, subnets, security groups)
- [ ] Deploy RDS PostgreSQL with schema
- [ ] Deploy S3 buckets with lifecycle policies
- [ ] Deploy Qdrant on EC2
- [ ] Set up Redis (ElastiCache or EC2)
- [ ] Create SQLAlchemy models and Alembic migrations

### Phase 2: Ingestion Pipelines (Weeks 3-4)

- [ ] Implement NSE/BSE filing crawlers
- [ ] Implement investor relations auto-discovery and crawler
- [ ] Implement PDF/PPT parsers with table extraction
- [ ] Implement chart extraction with vision LLM
- [ ] Implement news fetcher with sentiment analysis
- [ ] Set up Celery workers and SQS queues
- [ ] Configure EventBridge scheduled jobs

### Phase 3: Vector Search & Embeddings (Week 5)

- [ ] Implement chunking strategy
- [ ] Integrate OpenAI embeddings API
- [ ] Set up Qdrant collections and indexes
- [ ] Implement embedding pipeline (Celery task)
- [ ] Test semantic search queries

### Phase 4: LangGraph Agents (Weeks 6-7)

- [ ] Implement state model and graph structure
- [ ] Implement router node
- [ ] Implement company analysis node with tools
- [ ] Implement comparison node
- [ ] Implement portfolio node
- [ ] Implement news sentiment node
- [ ] Implement doc insight node
- [ ] Implement synthesis node with layman explanations
- [ ] Test full query flow

### Phase 5: FastAPI Backend (Week 8)

- [ ] Implement authentication and user management
- [ ] Implement query API endpoint
- [ ] Implement portfolio management endpoints
- [ ] Implement document upload endpoint
- [ ] Implement on-demand refresh API
- [ ] Implement task status polling API
- [ ] Set up WebSocket for streaming responses

### Phase 6: Monitoring & Optimization (Week 9)

- [ ] Set up CloudWatch logs and metrics
- [ ] Configure X-Ray tracing
- [ ] Set up alarms for latency, errors, queue depth
- [ ] Implement caching layer (Redis)
- [ ] Optimize slow queries
- [ ] Load testing and performance tuning

### Phase 7: Theme Detection & Discovery (Week 10)

- [ ] Implement offline theme tagging agent
- [ ] Implement hidden subdomain detection
- [ ] Test theme detection across sample companies
- [ ] Build discovery API endpoints

### Phase 8: Production Readiness (Weeks 11-12)

- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Implement backup and disaster recovery
- [ ] Security audit and hardening
- [ ] Documentation (API docs, runbooks)
- [ ] User acceptance testing
- [ ] Production deployment

---

## Success Metrics

### Technical Metrics

- **Query latency**: p95 < 3 seconds
- **Ingestion throughput**: 1000+ documents/day
- **Vector search latency**: p95 < 100ms
- **System uptime**: 99.5%+
- **Error rate**: < 1%

### Business Metrics

- **Company coverage**: 5000+ Indian companies
- **Document corpus**: 100k+ filings, presentations, reports
- **News articles**: 10k+ articles/month
- **User queries**: Sub-3-second responses
- **Insight quality**: Hidden themes detected with >70% confidence

---

## Risk Mitigation

### 1. **Data Quality**

- **Risk**: Incorrect financial data extraction
- **Mitigation**: Multi-stage validation, manual spot-checks, user feedback loop

### 2. **API Costs**

- **Risk**: High OpenAI API costs
- **Mitigation**: Caching, smaller models for embeddings, batch processing, rate limiting

### 3. **Crawling Failures**

- **Risk**: NSE/BSE website changes break crawlers
- **Mitigation**: Robust error handling, alerts, fallback to manual ingestion

### 4. **Scalability**

- **Risk**: System can't handle 50k+ companies
- **Mitigation**: Horizontal scaling (workers, Qdrant sharding), database partitioning

### 5. **Compliance**

- **Risk**: Data privacy, SEBI regulations
- **Mitigation**: User data encryption, audit logs, compliance review

---

## Next Steps

1. **Review and approve** this architecture refinement
2. **Set up development environment** (local Docker Compose for Postgres, Redis, Qdrant)
3. **Start Phase 1** (Core Data Infrastructure)
4. **Weekly progress reviews** to adjust roadmap as needed

---

## Conclusion

This refined architecture provides a **production-grade, scalable, and intelligent** equity research platform that:

- **Autonomously ingests** data from NSE/BSE, investor sites, and news sources
- **Processes complex documents** with tables, charts, and graphics
- **Discovers hidden insights** through theme detection and second-order reasoning
- **Provides portfolio intelligence** with concentration risk and red flag detection
- **Explains in layman terms** adapted to user expertise level
- **Scales efficiently** with cloud-native architecture and asynchronous processing
- **Costs ~$400-500/month** for MVP scale

The system is designed to be **VC-fundable** and can scale to serve 10k+ users with minimal architectural changes.
