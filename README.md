# AI Equity Research Platform

AI-native equity research platform for Indian equities (NSE/BSE). Provides institutional-grade research capabilities to retail investors via LLM-powered agents, RAG over financial filings, and automated analysis.

## Services

| Service | Port | Tech |
|---------|------|------|
| **Frontend** | 5173 | React 19, TypeScript, Vite, Recharts |
| **Backend** | 8001 | FastAPI, LangGraph, SQLAlchemy, Qdrant, httpx (FMP, FRED, NewsAPI, Upstox, Kite) |
| **PostgreSQL** | 5432 | Companies, financials, users, portfolios |
| **Redis** | 6379 | Caching, Celery broker |
| **Qdrant** | 6333 | Vector search over filings |

## Quick Start

```bash
docker compose up -d                                          # infrastructure
python3 -m venv backend-ai/.venv && source backend-ai/.venv/bin/activate  # backend virtual env
pip install -r backend-ai/requirements.txt                    # backend dependencies
cp backend-ai/.env.example backend-ai/.env                    # configure backend env
python backend-ai/scripts/seed_db.py                          # seed database
cd backend-ai && python -m uvicorn src.main:app --port 8001 --reload &  # backend
cd ../frontend && npm install && npm run dev                  # frontend
```

Open http://localhost:5173 and switch to **Live** mode.

## Features

- **Iris Chat** -- AI research copilot with persistent threads and mode-aware responses
- **Company Analysis** -- financial statements, ratios, risk flags, theme exposure
- **Company Comparison** -- side-by-side analysis of 2-5 companies
- **Portfolio Management** -- holdings tracking, concentration analysis, sector exposure
- **News & Sentiment** -- market headlines with bullish/bearish classification
- **Document Upload** -- upload PDFs/PPTs for AI analysis via RAG
- **Screening & Discovery** -- filter stocks by sector, industry, market cap
- **Watchlists** -- track companies of interest
- **Personalized Alerts** -- set rules for price, sentiment, filing triggers
- **Timeline** -- aggregated feed of filings and news
- **Deep Research** -- CLI-based multi-agent orchestrator for deep analysis

## Documentation

See **[GETTING_STARTED.md](GETTING_STARTED.md)** for the full setup guide, feature documentation, API reference, and troubleshooting.

## Repository Notes

- Python dependencies are maintained in `backend-ai/requirements.txt`.
- Operational backend scripts live in `backend-ai/scripts/` (seeding, debug helpers, local model setup).

## Tech Stack

- **LLM:** Groq / Ollama / OpenAI / DeepSeek (configurable)
- **Agents:** LangGraph with Router, 5 specialist agents, and Synthesis
- **Database:** PostgreSQL 15 with 19 SQLAlchemy models
- **Vector Search:** Qdrant for semantic search over company filings
- **Frontend:** React 19 with demo/live data modes
- **Data APIs:** FMP, FRED, NewsAPI, NewsData.io, Upstox, Kite Connect
