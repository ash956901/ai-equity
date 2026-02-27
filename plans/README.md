# AI Equity Research Platform – Planning Documents

This directory contains comprehensive architecture and design documentation for the AI-native equity research platform, refined from the initial ChatGPT proposal into a production-ready, backend-only system optimized for Indian equities.

---

## Quick Start

**Start here**: [`ARCHITECTURE_OVERVIEW.md`](./ARCHITECTURE_OVERVIEW.md) – Concise summary of the entire system

**Original proposal**: [`chatgpt.txt`](./chatgpt.txt) – Initial design from ChatGPT (for reference)

---

## Core Documentation

### 0. Summary & Overview

- **[00_architecture_refinement_summary.md](./00_architecture_refinement_summary.md)**  
  Comprehensive summary of all design decisions, components, and implementation roadmap

- **[ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md)**  
  Concise, copy-paste ready architecture overview

### 1. Database Design

- **[01_database_schema.md](./01_database_schema.md)**  
  Complete PostgreSQL schema with:
  - Companies, securities, indices (NSE/BSE)
  - Financial statements and ratios
  - Filings, news, themes
  - Portfolios, holdings, transactions
  - Chat sessions, user uploads
  - ETL runs and system config

### 2. Data Ingestion

- **[02_ingestion_pipelines.md](./02_ingestion_pipelines.md)**  
  Crawling and ETL pipelines for:
  - NSE/BSE regulatory filings
  - Investor relations sites (auto-discovery)
  - News sources (GNews, NewsAPI, RSS)
  - PDF/PPT parsing with table and chart extraction
  - Embedding generation and theme tagging

### 3. Vector Search

- **[03_vector_store_strategy.md](./03_vector_store_strategy.md)**  
  Vector database strategy with:
  - Qdrant vs pgvector decision (chose Qdrant)
  - Collection design (filings, news, user uploads)
  - Chunking and embedding strategy
  - Query patterns (semantic, temporal, hybrid)
  - Performance optimization

### 4. Agent Architecture

- **[04_langgraph_agent_design.md](./04_langgraph_agent_design.md)**  
  LangGraph agent design with:
  - State model and graph structure
  - Router, analysis, comparison, portfolio, news, doc agents
  - Synthesis agent with layman explanations
  - Tool definitions (financial, vector, news, portfolio)
  - Memory integration

### 5. Cloud Deployment

- **[05_cloud_deployment_strategy.md](./05_cloud_deployment_strategy.md)**  
  AWS deployment architecture with:
  - Compute (ECS Fargate, EC2)
  - Data (RDS PostgreSQL, ElastiCache Redis, S3, Qdrant)
  - Async processing (Celery + SQS)
  - Scheduled jobs (EventBridge)
  - Near-time query handling
  - Monitoring (CloudWatch, X-Ray)
  - Cost estimation (~$400-500/month)

---

## Key Design Decisions

| Aspect | Decision | Document |
|--------|----------|----------|
| **Agent Framework** | LangGraph (over CrewAI) | [04_langgraph_agent_design.md](./04_langgraph_agent_design.md) |
| **Vector DB** | Qdrant (over pgvector) | [03_vector_store_strategy.md](./03_vector_store_strategy.md) |
| **Cloud Provider** | AWS | [05_cloud_deployment_strategy.md](./05_cloud_deployment_strategy.md) |
| **Database** | PostgreSQL | [01_database_schema.md](./01_database_schema.md) |
| **Workers** | Celery + SQS | [05_cloud_deployment_strategy.md](./05_cloud_deployment_strategy.md) |
| **Embeddings** | OpenAI text-embedding-3-small | [03_vector_store_strategy.md](./03_vector_store_strategy.md) |
| **LLM** | OpenAI GPT-4o | [04_langgraph_agent_design.md](./04_langgraph_agent_design.md) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User / Client                           │
└────────────────────────┬────────────────────────────────────┘
                         │ REST / WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  - Authentication                                            │
│  - Query routing                                             │
│  - API endpoints                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  LangGraph   │  │  Background  │  │  Scheduled   │
│    Agents    │  │   Workers    │  │    Jobs      │
│              │  │   (Celery)   │  │(EventBridge) │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       └─────────────────┴──────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Qdrant    │  │      S3      │
│  (Structured │  │   (Vector    │  │  (Documents, │
│     Data)    │  │    Search)   │  │    Charts)   │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Key Features

1. **Autonomous Discovery** – Auto-discovers investor relations URLs
2. **Complex Document Understanding** – Tables, charts, graphics via vision LLM
3. **Hidden Insights** – Theme detection, second-order effects
4. **India-First** – NSE/BSE, INR, Indian sectors, RBI/SEBI context
5. **Portfolio Intelligence** – Concentration risk, sector allocation, red flags
6. **Layman Explanations** – Adaptive to user expertise level
7. **Real-Time News Sentiment** – Hourly fetch with FinBERT analysis

---

## Implementation Roadmap

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 1** | Weeks 1-2 | Core infrastructure (AWS, DB, S3, Qdrant) |
| **Phase 2** | Weeks 3-4 | Ingestion pipelines (crawlers, parsers) |
| **Phase 3** | Week 5 | Vector search & embeddings |
| **Phase 4** | Weeks 6-7 | LangGraph agents |
| **Phase 5** | Week 8 | FastAPI backend |
| **Phase 6** | Week 9 | Monitoring & optimization |
| **Phase 7** | Week 10 | Theme detection & discovery |
| **Phase 8** | Weeks 11-12 | Production readiness |

---

## Technology Stack

**Backend**: Python 3.11, FastAPI, LangGraph, Pydantic, SQLAlchemy  
**Data**: PostgreSQL 15, Qdrant, Redis, AWS S3  
**Crawling**: Scrapy, Playwright, PyMuPDF, pdfplumber, python-pptx  
**ML/AI**: OpenAI GPT-4o, text-embedding-3-small, FinBERT  
**Infrastructure**: AWS ECS Fargate, RDS, ElastiCache, SQS, EventBridge  
**Workers**: Celery with SQS broker  
**Monitoring**: CloudWatch, X-Ray, Structlog  

---

## Success Metrics

**Technical**:
- Query latency: p95 < 3 seconds
- Vector search: p95 < 100ms
- System uptime: 99.5%+
- Error rate: < 1%

**Business**:
- 5000+ Indian companies
- 100k+ documents
- 10k+ news articles/month
- Hidden themes with >70% confidence

---

## Cost Estimate

**MVP Scale** (~100s of users): **$400-500/month**

Breakdown:
- ECS Fargate (API + Workers): $90
- RDS PostgreSQL: $80
- ElastiCache Redis: $50
- Qdrant (EC2): $70
- S3 + Data Transfer: $25
- SQS + CloudWatch: $25
- OpenAI API: $50-150

**Optimization strategies**:
- EC2 Spot Instances for workers (-70%)
- S3 Intelligent Tiering (-40%)
- RDS Reserved Instances after 6 months (-40%)

---

## Next Steps

1. **Review** all documentation
2. **Set up** development environment (Docker Compose)
3. **Begin Phase 1**: AWS infrastructure setup
4. **Weekly reviews** to track progress and adjust

---

## Questions or Clarifications?

For any questions about the architecture, design decisions, or implementation details, refer to the specific document linked above or reach out to the team.

---

**This architecture is production-ready, scalable, and designed to be VC-fundable.**
