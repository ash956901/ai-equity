# AI Equity Research Platform – Architecture Overview

**Backend-Only, Agent-Centric System for Indian Equities**

---

## Core Architecture

### Technology Stack

**Backend**: Python 3.11, FastAPI, LangGraph, Pydantic, SQLAlchemy  
**Data**: PostgreSQL 15, Qdrant (vector DB), Redis, AWS S3  
**ML/AI**: OpenAI GPT-4o, text-embedding-3-small, FinBERT  
**Infrastructure**: AWS (ECS Fargate, RDS, ElastiCache, SQS, EventBridge)  
**Workers**: Celery with SQS broker  

---

## System Design

```
User → FastAPI → LangGraph Agents → {PostgreSQL, Qdrant, S3}
                       ↓
              Background Workers (Celery)
                       ↓
         {NSE/BSE, IR Sites, News, Documents}
```

---

## Key Components

### 1. Database (PostgreSQL)

**Core Tables**:
- Companies, securities, indices (NSE/BSE mapping)
- Financial statements (raw + ratios)
- Filings, news articles (with sentiment)
- Portfolios, holdings, transactions
- Chat sessions, user uploads
- Company themes (AI, defense, data centers, etc.)

### 2. Ingestion Pipelines

**Sources**:
- NSE/BSE regulatory filings (daily)
- Company investor relations sites (auto-discovered, weekly)
- News (GNews, NewsAPI, RSS - hourly)

**Processing**:
- PDF/PPT parsing with table extraction
- Chart extraction via vision LLM
- Financial statement normalization
- Sentiment analysis (FinBERT)
- Embedding generation (OpenAI)

### 3. Vector Store (Qdrant)

**Collections**:
- `company_filings`: All parsed filings, presentations, concalls
- `news_articles`: News with sentiment metadata
- `user_uploads`: Per-user document namespaces

**Chunking**: 500-1000 tokens, 100-token overlap  
**Embeddings**: OpenAI text-embedding-3-small (1536 dims)

### 4. LangGraph Agents

**Query Flow**:
```
Router → {CompanyAnalysis | Comparison | Portfolio | News | DocInsight} → Synthesis
```

**Agents**:
- **Router**: Classify intent, extract entities
- **CompanyAnalysis**: Financials, ratios, filings, news, themes, risk flags
- **Comparison**: Multi-company comparison across growth, margins, valuation, risk
- **Portfolio**: Holdings, concentration, sector allocation, risk analysis
- **NewsSentiment**: Semantic news search, sentiment aggregation
- **DocInsight**: User upload analysis
- **Synthesis**: LLM reasoning + "Explained Simply" section

**Tools** (non-LLM): All math, ratios, portfolio metrics, data access  
**LLM**: Interpretation, reasoning, synthesis only

### 5. Cloud Deployment (AWS)

**Compute**:
- FastAPI: ECS Fargate (2 tasks, auto-scaling)
- Workers: ECS Fargate/EC2 Spot (cost-optimized)

**Data**:
- PostgreSQL: RDS (db.t3.medium, Multi-AZ)
- Redis: ElastiCache (cache.t3.medium)
- S3: Object storage with lifecycle policies
- Qdrant: EC2 (t3.large) with daily S3 snapshots

**Async Processing**:
- Celery + SQS (separate queues: crawlers, parsers, embeddings, news)
- EventBridge for scheduled jobs

**Cost**: ~$400-500/month (MVP scale)

---

## Key Features

### 1. Autonomous Discovery
- Auto-discovers investor relations URLs via sitemap parsing
- No manual URL input required

### 2. Complex Document Understanding
- Tables: Extract and normalize P&L, BS, CF
- Charts: Vision LLM extracts structured data from graphs
- Mixed PDFs/PPTs with tables, charts, text

### 3. Hidden Insights
- Theme detection: AI, defense, renewables, EV, data centers
- Second-order effects (e.g., Castrol → data center coolants)
- Subdomain exposure analysis

### 4. India-First
- NSE/BSE tickers, INR currency, Cr/Lakh units
- Indian sector classifications
- RBI/SEBI/Budget as macro inputs

### 5. Portfolio Intelligence
- Broker integration (Zerodha, Kotak, Groww)
- Concentration risk (Herfindahl index)
- Sector allocation, beta vs Nifty
- Red flag detection across holdings

### 6. Layman Explanations
- User expertise level (beginner/intermediate/advanced)
- Adaptive explanation depth
- Always includes "Explained Simply" section

### 7. Real-Time News Sentiment
- Hourly news fetch
- FinBERT sentiment analysis
- Impact classification (High/Med/Low)

---

## Data Flow

### Ingestion (Async)
```
Scheduler → Crawler → Parser → {Table/Chart Extractor, Embedder} → DB/Vector Store
```

### Query (Sync)
```
User Query → Router → Specialized Agent → Tools (DB/Vector queries) → Synthesis → Response
```

### Near-Time Queries
- Pre-computed tables (financial_ratios, portfolio_metrics)
- Redis caching (5-min TTL)
- On-demand refresh API with task status polling
- WebSocket streaming for real-time updates

---

## Implementation Phases

**Phase 1 (Weeks 1-2)**: Core infrastructure (AWS, PostgreSQL, S3, Qdrant, Redis)  
**Phase 2 (Weeks 3-4)**: Ingestion pipelines (crawlers, parsers, embeddings)  
**Phase 3 (Week 5)**: Vector search & embeddings  
**Phase 4 (Weeks 6-7)**: LangGraph agents  
**Phase 5 (Week 8)**: FastAPI backend  
**Phase 6 (Week 9)**: Monitoring & optimization  
**Phase 7 (Week 10)**: Theme detection & discovery  
**Phase 8 (Weeks 11-12)**: Production readiness  

---

## Success Metrics

**Technical**:
- Query latency: p95 < 3s
- Vector search: p95 < 100ms
- Uptime: 99.5%+
- Error rate: < 1%

**Business**:
- 5000+ Indian companies
- 100k+ documents
- 10k+ news articles/month
- Hidden themes with >70% confidence

---

## Architecture Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| **Agent Framework** | LangGraph | Deterministic, production-grade, explicit control |
| **Vector DB** | Qdrant | Scale, performance, hybrid search |
| **Cloud** | AWS | Mature ecosystem, S3, cost-effective |
| **Workers** | Celery + SQS | Battle-tested, auto-scaling, managed queue |
| **Database** | PostgreSQL | Relational integrity, mature, cloud-managed |
| **Embeddings** | OpenAI | State-of-art quality, affordable |
| **LLM** | GPT-4o | Best reasoning, synthesis quality |

---

## Detailed Documentation

1. **[Database Schema](./01_database_schema.md)** – Full PostgreSQL schema with India-specific fields
2. **[Ingestion Pipelines](./02_ingestion_pipelines.md)** – Crawlers, parsers, ETL orchestration
3. **[Vector Store Strategy](./03_vector_store_strategy.md)** – Qdrant setup, chunking, query patterns
4. **[LangGraph Agent Design](./04_langgraph_agent_design.md)** – State model, nodes, tools, memory
5. **[Cloud Deployment](./05_cloud_deployment_strategy.md)** – AWS architecture, cost, monitoring

---

## Next Steps

1. Review and approve architecture
2. Set up development environment (Docker Compose)
3. Begin Phase 1: Core infrastructure
4. Weekly progress reviews

---

**This architecture is production-ready, scalable to 50k+ companies, and designed to be VC-fundable.**
