# AI Equity Research Platform - Getting Started Guide

A complete guide to setting up, running, and using every part of the platform from scratch.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Quick Start (5 minutes)](#3-quick-start-5-minutes)
4. [Detailed Setup Guide](#4-detailed-setup-guide)
   - [Step 1: Infrastructure (Docker)](#step-1-infrastructure-docker)
   - [Step 2: Environment Configuration](#step-2-environment-configuration)
   - [Step 3: Backend (Unified Server)](#step-3-backend-unified-server)
   - [Step 4: Frontend (React SPA)](#step-4-frontend-react-spa)
   - [Step 5: Database Seeding](#step-5-database-seeding)
5. [Verifying the Setup](#5-verifying-the-setup)
6. [Feature Guide](#6-feature-guide)
   - [Iris Chat (AI Research Copilot)](#61-iris-chat-ai-research-copilot)
   - [Company Analysis](#62-company-analysis)
   - [Company Comparison](#63-company-comparison)
   - [Portfolio Management](#64-portfolio-management)
   - [News and Sentiment](#65-news-and-sentiment)
   - [Document Upload and Analysis](#66-document-upload-and-analysis)
   - [Screening and Discovery](#67-screening-and-discovery)
   - [Watchlists](#68-watchlists)
   - [Personalized Alerts](#69-personalized-alerts)
   - [Timeline](#610-timeline)
   - [Deep Research Orchestrator (CLI)](#611-deep-research-orchestrator-cli)
7. [API Reference](#7-api-reference)
   - [AI & Platform APIs](#ai--platform-apis)
   - [External Data APIs](#external-data-apis)
8. [LLM Configuration](#8-llm-configuration)
9. [Database Management](#9-database-management)
10. [Troubleshooting](#10-troubleshooting)
11. [Project Structure](#11-project-structure)

---

## 1. Architecture Overview

The platform is composed of two services and three infrastructure containers:

```
                      +-------------------+
                      |  Frontend (React)  |
                      |   localhost:5173   |
                      +---------+---------+
                                |
                    +-----------v-----------+
                    |  Backend (Unified)    |
                    |   localhost:8001      |
                    |                       |
                    | LangGraph Agents      |
                    | FMP, FRED, NewsAPI    |
                    | NewsDataIO, Upstox   |
                    | Kite Connect          |
                    | Chat, Companies,      |
                    | Portfolio, Compare,   |
                    | Alerts, Watchlists,   |
                    | Timeline, Screens,    |
                    | File Upload           |
                    +-----------+-----------+
                                |
                 +--------------+--------------+
                 |              |              |
       +---------v---+ +-------v-----+ +------v------+
       | PostgreSQL  | |    Redis    | |   Qdrant    |
       | port 5432   | |  port 6379  | |  port 6333  |
       +-------------+ +-------------+ +-------------+
```

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 5173 | React SPA with demo/live data modes |
| Backend | 8001 | LangGraph agents, external data APIs, database, vector search, AI chat |
| PostgreSQL | 5432 | Primary database (companies, financials, users, portfolios) |
| Redis | 6379 | Caching and Celery task broker |
| Qdrant | 6333 | Vector database for semantic search over filings |

---

## 2. Prerequisites

| Tool | Version | Check Command |
|------|---------|---------------|
| Docker & Docker Compose | 20+ | `docker --version` |
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

**Required API key (at least one LLM provider):**

| Provider | Cost | Notes |
|----------|------|-------|
| Groq | Free tier available | Recommended for development. Sign up at https://console.groq.com |
| Ollama | Free (local) | Requires downloading models. Install from https://ollama.com |
| OpenAI | Paid | GPT-4o-mini or GPT-4o |
| DeepSeek | Paid | DeepSeek API |

**Optional API keys (for the data backend):**
- FMP (Financial Modeling Prep) - US market data
- FRED (Federal Reserve) - macro economic data
- NewsAPI / NewsData.io - news feeds
- Upstox / Kite - Indian broker integration

---

## 3. Quick Start (5 minutes)

Run all of this from the `ai-equity/` directory:

```bash
cd ai-equity

# 1. Start infrastructure
docker compose up -d

# 2. Create Python virtual environment and install deps
python3 -m venv backend-ai/.venv
source backend-ai/.venv/bin/activate
pip install -r backend-ai/requirements.txt

# 3. Configure environment
cp backend-ai/.env.example backend-ai/.env
# Edit backend-ai/.env and add your LLM API key (see Step 2 below)

# 4. Seed the database
python backend-ai/scripts/seed_db.py

# 5. Start the backend (terminal 1)
cd backend-ai && python -m uvicorn src.main:app --port 8001 --reload

# 6. Start the frontend (terminal 2)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 in your browser. Toggle **Live** mode in the sidebar to connect to the real backends.

---

## 4. Detailed Setup Guide

### Step 1: Infrastructure (Docker)

Start PostgreSQL, Redis, and Qdrant:

```bash
cd ai-equity
docker compose up -d
```

Verify all containers are healthy:

```bash
docker compose ps
```

Expected output:
```
NAME                   STATUS         PORTS
ai-equity-postgres-1   Up (healthy)   0.0.0.0:5432->5432/tcp
ai-equity-redis-1      Up (healthy)   0.0.0.0:6379->6379/tcp
ai-equity-qdrant-1     Up             0.0.0.0:6333->6333/tcp
```

Verify connectivity:
```bash
# PostgreSQL
docker exec ai-equity-postgres-1 pg_isready -U postgres

# Redis
docker exec ai-equity-redis-1 redis-cli ping

# Qdrant
curl http://localhost:6333/healthz
```

**To stop infrastructure:**
```bash
docker compose down          # stop containers (keeps data)
docker compose down -v       # stop and DELETE all data
```

---

### Step 2: Environment Configuration

Copy the template and edit:

```bash
cp backend-ai/.env.example backend-ai/.env
```

**Minimum required configuration** -- edit `backend-ai/.env` and set one LLM provider:

#### Option A: Groq (recommended, free tier)

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

Get a key at https://console.groq.com/keys

#### Option B: Ollama (local, free)

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=deepseek-r1:8b
OLLAMA_BASE_URL=http://localhost:11434
```

Then download the model:
```bash
ollama pull deepseek-r1:8b
ollama pull nomic-embed-text
```

#### Option C: OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your_key_here
OPENAI_MODEL=gpt-4o-mini
```

#### Embeddings configuration

For Ollama embeddings (default):
```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
```

For OpenAI embeddings:
```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

#### Optional: External data API keys

Add these to your `backend-ai/.env` file:
```env
FMP_API_KEY=your_key
NEWS_API_KEY=your_key
NEWSDATA_API_KEY=your_key
UPSTOX_API_KEY=your_key
UPSTOX_ACCESS_TOKEN=your_token
KITE_API_KEY=your_key
KITE_ACCESS_TOKEN=your_token
```

---

### Step 3: Backend (Unified Server)

The backend serves both AI agent endpoints and external data API proxies on a single port (8001).

```bash
cd ai-equity

# Create virtual environment (skip if already done)
python3 -m venv backend-ai/.venv
source backend-ai/.venv/bin/activate

# Install dependencies
pip install -r backend-ai/requirements.txt

# Start the server
cd backend-ai
python -m uvicorn src.main:app --port 8001 --reload
```

On startup, `init_db()` auto-creates all database tables.

**Verify it works:**
```bash
curl http://localhost:8001/health
# {"status":"healthy"}

curl http://localhost:8001/
# {"status":"ok","service":"ai-equity-research","version":"0.1.0"}
```

**Swagger API docs:** http://localhost:8001/docs

**Note:** External data API endpoints (FMP, FRED, NewsAPI, etc.) work without API keys -- they return errors for unconfigured providers, but the server starts fine. The frontend falls back to demo data if calls fail.

---

### Step 4: Frontend (React SPA)

```bash
cd ai-equity/frontend
npm install
npm run dev
```

Output:
```
VITE v6.4.1 ready in 542 ms
  Local:   http://localhost:5173/
```

**Open http://localhost:5173** in your browser.

**Data mode toggle:** In the sidebar, you can switch between:
- **Demo** -- uses built-in mock data (no backend needed)
- **Live** -- calls the real backends (requires backends running)

**Custom backend URL** (optional): Create `frontend/.env`:
```env
VITE_BACKEND_URL=http://localhost:8001
```

**Production build:**
```bash
npm run build
npm run preview    # preview the production build
```

---

### Step 5: Database Seeding

Populate the database with 20 Indian companies, financial ratios, themes, news, and a test user:

```bash
cd ai-equity
source backend-ai/.venv/bin/activate
python backend-ai/scripts/seed_db.py
```

Output:
```
Seeded 20 companies, 5 ratio sets, 17 themes, 8 news articles, 1 user with portfolio (5 holdings)
Test user ID: <uuid>
Test user email: test@equityai.dev
```

**Save the test user ID** -- you need it for API calls and the frontend stores it in localStorage.

The seed creates:
- 20 companies: Reliance, TCS, HDFC Bank, Infosys, ICICI Bank, HUL, SBI, Airtel, ITC, L&T, Kotak, Axis, Wipro, HCL Tech, Sun Pharma, Maruti, Bajaj Finance, Asian Paints, Titan, Adani Enterprises
- Financial ratios for top 5 companies (ROE, ROCE, margins, P/E, etc.)
- 17 theme tags (AI, 5G, Green Energy, Infrastructure, Digital Banking, etc.)
- 8 news articles with sentiment labels
- 1 test user with a portfolio containing 5 holdings

---

## 5. Verifying the Setup

Run these checks to confirm everything is working:

```bash
# 1. Infrastructure
docker compose ps                                    # all containers Up

# 2. Backend
curl -s http://localhost:8001/health                  # {"status":"healthy"}
curl -s http://localhost:8001/companies/ | head -c 200  # list of companies

# 3. AI Chat query (replace USER_ID with your test user ID)
curl -s -X POST http://localhost:8001/chat/query \
  -H "Content-Type: application/json" \
  -d '{"user_id":"YOUR_TEST_USER_ID","query":"Analyze Reliance Industries","expertise_level":"intermediate"}'

# 4. Frontend
# Open http://localhost:5173, switch to Live mode, go to Iris Chat
```

---

## 6. Feature Guide

### 6.1 Iris Chat (AI Research Copilot)

The core feature. An AI assistant that answers equity research questions using LangGraph agents.

**How to use (Frontend):**
1. Go to the **Iris Chat** view in the sidebar
2. Ensure **Live** mode is active (toggle in sidebar)
3. Type a query and press Enter

**What it does internally:**
1. Query goes to `POST /chat/query` on the AI backend
2. The **Router Agent** classifies the query (company analysis, comparison, portfolio, news, document)
3. Routes to the correct specialist agent(s)
4. Each agent fetches data from the database, Qdrant, or external tools
5. The **Synthesis Agent** produces a final response using the LLM
6. Response includes the analysis, sources, execution plan, and agent logs

**Modes:**
- **Analyst Mode** -- detailed technical analysis with data tables
- **Simple Mode** -- layman-friendly explanations (maps to `expertise_level: beginner`)

**Example queries:**
```
"Analyze the financial health of Reliance Industries"
"Compare TCS vs Infosys on growth and profitability"
"Show my portfolio risk exposure"
"What is the latest news sentiment for HDFC Bank?"
"Explain why the defense theme is heating up"
```

**API:**
```bash
curl -X POST http://localhost:8001/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "query": "Analyze Reliance Industries financials",
    "expertise_level": "intermediate"
  }'
```

Response includes: `response`, `sources`, `execution_plan`, `agent_outputs`, `session_id`

---

### 6.2 Company Analysis

View financial data, ratios, and AI-generated analysis for any company.

**API endpoints:**
```bash
# List all companies
curl http://localhost:8001/companies/

# Get company details
curl http://localhost:8001/companies/{company_id}

# Get financial statements (last 4 quarters)
curl http://localhost:8001/companies/{company_id}/financials?periods=4

# Get financial ratios
curl http://localhost:8001/companies/{company_id}/ratios
```

**Ratios returned:** ROE, ROCE, gross/EBITDA/net margin, debt-to-equity, interest coverage, current ratio, P/E, P/B, revenue growth YoY, PAT growth YoY, EPS growth YoY.

---

### 6.3 Company Comparison

Compare 2-5 companies side by side using the AI agent.

**API:**
```bash
curl -X POST http://localhost:8001/compare/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "company_ids": ["COMPANY_ID_1", "COMPANY_ID_2"],
    "query": "Compare on growth, profitability, and valuation",
    "expertise_level": "intermediate"
  }'
```

The comparison agent fetches financials and ratios for each company, then the synthesis agent generates a side-by-side analysis.

---

### 6.4 Portfolio Management

Manage investment portfolios with holdings tracking.

**API:**
```bash
# List portfolios
curl "http://localhost:8001/portfolios/?user_id=YOUR_USER_ID"

# Create a portfolio
curl -X POST http://localhost:8001/portfolios/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"YOUR_USER_ID","name":"Growth Portfolio"}'

# Get portfolio with holdings and metrics
curl http://localhost:8001/portfolios/{portfolio_id}

# Add a holding
curl -X POST http://localhost:8001/portfolios/{portfolio_id}/holdings \
  -H "Content-Type: application/json" \
  -d '{"company_id":"COMPANY_ID","quantity":100,"average_price":2800}'
```

Portfolio metrics include: total value, concentration analysis, sector exposure, and individual holding P&L.

---

### 6.5 News and Sentiment

View market news with sentiment analysis.

**Via external news APIs:**
```bash
# Market headlines
curl "http://localhost:8001/newsdata/market/headlines?country=in&timeframe=6&size=6"

# Ticker sentiment
curl "http://localhost:8001/newsdata/sentiment/RELIANCE?hours_back=24&size=8&language=en"
```

**Via database news:**
News articles in the database include sentiment labels (bullish/bearish/neutral) and impact levels. The News Sentiment agent uses these in chat queries.

---

### 6.6 Document Upload and Analysis

Upload PDF, PPTX, or other documents for AI analysis.

**API:**
```bash
curl -X POST http://localhost:8001/chat/upload \
  -F "file=@/path/to/annual_report.pdf" \
  -F "user_id=YOUR_USER_ID"
```

Response:
```json
{
  "upload_id": "uuid",
  "filename": "annual_report.pdf",
  "status": "uploaded",
  "file_size": 1234567,
  "hash": "abc123def456"
}
```

**Supported formats:** PDF, PPTX, PPT, TXT, CSV, XLSX (max 50MB)

After uploading, ask about the document in Iris Chat. The Doc Insight agent uses vector search over uploaded documents.

---

### 6.7 Screening and Discovery

Filter and screen stocks by sector, industry, and market cap.

**API:**
```bash
# Run a screen
curl -X POST http://localhost:8001/screens/run \
  -H "Content-Type: application/json" \
  -d '{"sector":"Information Technology","min_market_cap":200000,"limit":10}'

# Save a screen for later
curl -X POST http://localhost:8001/screens/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"YOUR_USER_ID",
    "name":"Large Cap IT",
    "filters":{"sector":"Information Technology","min_market_cap":200000}
  }'

# List saved screens
curl "http://localhost:8001/screens/?user_id=YOUR_USER_ID"
```

---

### 6.8 Watchlists

Track companies you are interested in.

**API:**
```bash
# Create a watchlist
curl -X POST http://localhost:8001/watchlists/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"YOUR_USER_ID","name":"Tech Stocks"}'

# Add a company
curl -X POST http://localhost:8001/watchlists/{watchlist_id}/companies \
  -H "Content-Type: application/json" \
  -d '{"company_id":"COMPANY_ID"}'

# List watchlists
curl "http://localhost:8001/watchlists/?user_id=YOUR_USER_ID"

# Remove a company
curl -X DELETE http://localhost:8001/watchlists/{watchlist_id}/companies/{company_id}
```

---

### 6.9 Personalized Alerts

Set up alert rules that trigger on price, volume, sentiment, or filing conditions.

**API:**
```bash
# Create an alert
curl -X POST http://localhost:8001/alerts/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"YOUR_USER_ID",
    "name":"Reliance price above 3000",
    "condition_type":"price_above",
    "condition_config":{"symbol":"RELIANCE","threshold":3000}
  }'

# List alerts
curl "http://localhost:8001/alerts/?user_id=YOUR_USER_ID"

# Delete an alert
curl -X DELETE http://localhost:8001/alerts/{alert_id}
```

**Condition types:** `price_above`, `price_below`, `volume_spike`, `sentiment_change`, `filing_new`

---

### 6.10 Timeline

Aggregated feed of filings, news, and signals across your tracked companies.

**API:**
```bash
# Get timeline for all companies
curl "http://localhost:8001/timeline/?limit=20"

# Filter by company
curl "http://localhost:8001/timeline/?company_id=COMPANY_ID&limit=10"
```

Returns events sorted by timestamp (newest first), each with `event_type` (filing or news), title, summary, and metadata.

---

### 6.11 Deep Agent Runtime

The web backend already uses the deep-agent orchestrator for Iris chat.

Primary path:

- `POST /chat/query` -> orchestrator + specialist sub-agents

Useful local scripts (from repo root):

```bash
source backend-ai/.venv/bin/activate
python backend-ai/scripts/run_agent.py
python backend-ai/scripts/debug_run.py
python backend-ai/scripts/test_imports.py
```

---

## 7. API Reference

All APIs are served on a single server at port 8001.

### AI & Platform APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Health check |
| POST | `/chat/query` | Send a research query to the AI agent |
| GET | `/chat/sessions/{user_id}` | List chat sessions |
| POST | `/chat/upload` | Upload a document for analysis |
| GET | `/companies/` | List companies |
| GET | `/companies/{id}` | Company details |
| GET | `/companies/{id}/financials` | Financial statements |
| GET | `/companies/{id}/ratios` | Financial ratios |
| GET | `/portfolios/?user_id=` | List portfolios |
| POST | `/portfolios/` | Create portfolio |
| GET | `/portfolios/{id}` | Portfolio with holdings and metrics |
| POST | `/portfolios/{id}/holdings` | Add/update holding |
| POST | `/compare/` | Compare 2-5 companies |
| GET | `/alerts/?user_id=` | List alert rules |
| POST | `/alerts/` | Create alert rule |
| DELETE | `/alerts/{id}` | Delete alert rule |
| GET | `/watchlists/?user_id=` | List watchlists |
| POST | `/watchlists/` | Create watchlist |
| POST | `/watchlists/{id}/companies` | Add company to watchlist |
| DELETE | `/watchlists/{id}/companies/{cid}` | Remove company |
| GET | `/timeline/` | Aggregated timeline feed |
| GET | `/screens/?user_id=` | List saved screens |
| POST | `/screens/` | Save screen filter |
| POST | `/screens/run` | Execute a screen query |

### External Data APIs

| Prefix | Provider | Key Endpoints |
|--------|----------|---------------|
| `/fmp` | Financial Modeling Prep | `/company/profile/{symbol}`, `/quote/{symbol}`, `/financials/*`, `/sec/filings/{symbol}`, `/screener`, `/search/company` |
| `/fred` | Federal Reserve | `/series/{id}`, `/rates/interest`, `/inflation`, `/gdp` |
| `/news` | NewsAPI | `/headlines`, `/search`, `/stock/{symbol}`, `/sentiment/{symbol}` |
| `/newsdata` | NewsData.io | `/latest`, `/market`, `/ticker/{symbol}`, `/sentiment/{symbol}`, `/market/headlines` |
| `/upstox` | Upstox (Indian broker) | `/market-quote/*`, `/portfolio/holdings`, `/portfolio/positions`, `/orders` |
| `/kite` | Kite/Zerodha | `/quote/ltp`, `/instruments`, `/instruments/{exchange}` |

**Interactive API docs:** http://localhost:8001/docs

---

## 8. LLM Configuration

The platform supports four LLM providers. Change the provider in `backend-ai/.env`:

| Provider | `LLM_PROVIDER` | Default Model | Notes |
|----------|----------------|---------------|-------|
| Groq | `groq` | `openai/gpt-oss-20b` | Free tier, fast inference |
| Ollama | `ollama` | `deepseek-r1:8b` | Local, no API key needed |
| OpenAI | `openai` | `gpt-4o-mini` | Best quality, paid |
| DeepSeek | `deepseek` | `deepseek-chat` | Alternative API |

**To switch providers:**
1. Edit `backend-ai/.env` and set `LLM_PROVIDER` and the corresponding API key
2. Restart the backend-ai server

**To use a different model within a provider:**
```env
LLM_MODEL=your-preferred-model    # overrides the provider default
```

---

## 9. Database Management

### View database tables

```bash
docker exec -it ai-equity-postgres-1 psql -U postgres -d equity_research
\dt          -- list tables
\d companies -- describe a table
SELECT count(*) FROM companies;
```

### Run Alembic migrations

```bash
cd ai-equity
source backend-ai/.venv/bin/activate
cd backend-ai

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your changes"

# Apply migrations
alembic upgrade head

# Check current migration version
alembic current
```

### Reset the database

```bash
docker compose down -v                  # delete volumes
docker compose up -d                    # fresh containers
cd backend-ai && alembic upgrade head   # recreate tables
cd .. && python backend-ai/scripts/seed_db.py      # re-seed
```

---

## 10. Troubleshooting

### "Could not connect to backend" in the frontend
- Verify the backend is running: `curl http://localhost:8001/health`
- Check you are in **Live** mode (not Demo) in the sidebar
- Check browser console for CORS errors

### "Connection refused" on port 5432
- Docker may not be running: `docker compose ps`
- Start infrastructure: `docker compose up -d`

### "No response generated" from chat
- Check that a valid LLM provider is configured in `backend-ai/.env`
- Check backend-ai logs for errors (the terminal running uvicorn)
- Ensure the database has been seeded: `curl http://localhost:8001/companies/` should return companies

### Chat returns generic response without financial data
- Ensure the query mentions a company name or ticker that exists in the database
- Try explicit queries: `"Analyze RELIANCE financials"` or `"Analyze TCS ratios"`
- The router agent uses keyword matching and LLM classification to route queries

### psycopg2 build fails during pip install
- On macOS: `brew install postgresql` (provides `pg_config`)
- Or use a Python version compatible with pre-built wheels (3.11 or 3.12)

### Ollama embeddings not working
- Ensure Ollama is running: `ollama serve`
- Pull the model: `ollama pull nomic-embed-text`
- Verify: `curl http://localhost:11434/api/tags`

### Port already in use
- Kill the process: `kill $(lsof -ti:8001)` (for port 8001)
- Or use a different port: `python -m uvicorn src.main:app --port 8002`

---

## 11. Project Structure

```
ai-equity/
├── backend-ai/               # Unified backend server (port 8001)
│   ├── alembic/              #   Database migrations
│   ├── src/
│   │   ├── app/              #   FastAPI factory/middleware/routers/lifespan
│   │   ├── domains/          #   Domain routes + services
│   │   ├── services/         #   Shared business services
│   │   ├── integrations/     #   Market data provider ownership
│   │   ├── external_apis/    #   Legacy compatibility wrappers
│   │   ├── api/              #   Legacy route compatibility shims
│   │   ├── agents/           #   Deep orchestrator + sub-agents + tools
│   │   ├── etl/              #   Data ingestion and refresh tasks
│   │   ├── llm/              #   LLM/embedding factory
│   │   ├── db/               #   Database session + SQLAlchemy models
│   │   ├── config.py         #   Pydantic settings
│   │   └── main.py           #   Thin FastAPI entry point
│   ├── scripts/              #   Operational scripts
│   │   ├── seed_db.py
│   │   ├── run_agent.py
│   │   ├── debug_run.py
│   │   ├── test_imports.py
│   │   ├── download_models.ps1
│   │   └── README.md
│   └── requirements.txt
│
├── frontend/                 # React SPA (port 5173)
│   ├── src/
│   │   ├── lib/api.ts        #   API integration layer
│   │   ├── App.tsx           #   Main app (all views)
│   │   ├── index.css         #   Styles with CSS variables
│   │   └── main.tsx          #   Entry point
│   ├── package.json
│   └── vite.config.ts
│
├── plans/                    # Architecture documentation
├── docker-compose.yml        # Infrastructure containers
└── backend-ai/requirements.txt  # Python dependencies
```
