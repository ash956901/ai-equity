# EquityAI - Full System Startup Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- ngrok (for exposing local backend)

---

## Quick Start (All Services)

### 1. Start Infrastructure (Docker)

```bash
# Start PostgreSQL, Redis, Celery Broker
cd /Users/ashutoshkumar/MyWork/majorproject
docker-compose up -d
```

**What this starts:**
- PostgreSQL (port 5432) - Main database
- Redis (port 6379) - Celery broker + cache

---

### 2. Start Backend-AI

```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai

# Activate virtual environment
source .venv/bin/activate

# Run database migrations
alembic upgrade head

# Seed initial data (causal chains, sector exposures)
python -m src.etl.seed_causal_data

# Start FastAPI server (port 8001)
python -m uvicorn src.main:app --reload --port 8001
```

**In a new terminal - expose with ngrok:**
```bash
ngrok http 8001
```

---

### 3. Start Celery Workers

**Terminal 1 - Commodity Price Sync Worker:**
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate
celery -A src.etl.celery_app worker -l info -Q commodity_sync --hostname commodity@%h
```

**Terminal 2 - Geopolitical Event Monitor Worker:**
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate
celery -A src.etl.celery_app worker -l info -Q event_monitor --hostname events@%h
```

**Terminal 3 - News Sync Worker:**
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate
celery -A src.etl.celery_app worker -l info -Q news_sync --hostname news@%h
```

---

### 4. Start Celery Beat (Scheduler)

```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate
celery -A src.etl.celery_app beat -l info --scheduler redBeatRedisScheduler
```

**This schedules:**
- `sync_commodity_prices` - Every 6 hours
- `monitor_geopolitical_events` - Every 1 hour
- `sync_news` - Every 2 hours

---

### 5. Frontend (Development)

```bash
cd /Users/ashutoshkumar/MyWork/majorproject/frontend
npm install
npm run dev
```

**Or for Production (Vercel):**
```bash
# Already deployed - just use the URL
# https://frontend-six-lac-70.vercel.app
```

---

## Service Ports Summary

| Service | Port | URL |
|---------|------|-----|
| PostgreSQL | 5432 | (internal) |
| Redis | 6379 | (internal) |
| Backend API | 8001 | http://localhost:8001 |
| ngrok | 4040 | https://your-ngrok.io |
| Frontend (dev) | 5173 | http://localhost:5173 |
| Frontend (prod) | - | https://frontend-six-lac-70.vercel.app |

---

## One-Command Startup Script

Create `start_system.sh`:

```bash
#!/bin/bash

echo "🚀 Starting EquityAI System..."

# 1. Docker
echo "📦 Starting Docker services..."
docker-compose up -d
sleep 3

# 2. Backend
echo "⚡ Starting Backend..."
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate
alembic upgrade head 2>/dev/null
python -m uvicorn src.main:app --reload --port 8001 &
BACKEND_PID=$!

# 3. ngrok (run separately in new terminal)
echo "🔗 To expose backend: ngrok http 8001"

# 4. Celery Workers (run in separate terminals)
echo "📝 To start Celery workers, run these in new terminals:"
echo "   celery -A src.etl.celery_app worker -l info -Q commodity_sync"
echo "   celery -A src.etl.celery_app worker -l info -Q event_monitor"
echo "   celery -A src.etl.celery_app worker -l info -Q news_sync"
echo "   celery -A src.etl.celery_app beat -l info"

echo "✅ Backend running on http://localhost:8001"
echo "✅ Frontend: https://frontend-six-lac-70.vercel.app"

wait $BACKEND_PID
```

---

## Testing the Pipeline

### 1. Test Commodity Sync
```bash
curl -X POST http://localhost:8001/api/tasks/sync-commodities
```

### 2. Test Event Monitor
```bash
curl -X POST http://localhost:8001/api/tasks/monitor-events
```

### 3. Test Portfolio Suggestions (with Hidden Insights)
```bash
curl "http://localhost:8001/portfolios/suggestions?user_id=70b4937b-5468-4bb8-a51f-309f3548c562"
```

### 4. Check Celery Tasks
```bash
celery -A src.etl.celery_app inspect active
celery -A src.etl.celery_app inspect scheduled
```

---

## Troubleshooting

### Redis Connection Error
```bash
# Check Redis is running
docker ps | grep redis
# Restart Redis
docker-compose restart redis
```

### Celery Worker Not Picking Tasks
```bash
# Check queue names match
# In celery_app.py, queues defined must match worker -Q argument
```

### Backend 500 Error
```bash
# Check logs
tail -f backend-ai/logs/app.log
# Or check PostgreSQL connection
python -c "from src.db.database import engine; engine.connect()"
```

---

## Environment Variables Required

Create `.env` in `backend-ai/`:

```env
# Database
DATABASE_URL=postgresql://equityai:equityai@localhost:5432/equityai

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# API Keys (free tiers)
OILPRICEAPI_KEY=your_key_here
GDELT_API_KEY=your_key_here

# LLM (for Iris)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

---

## File Structure

```
majorproject/
├── docker-compose.yml          # PostgreSQL, Redis
├── backend-ai/
│   ├── src/
│   │   ├── etl/
│   │   │   ├── celery_app.py       # Celery config
│   │   │   ├── commodity_sync_task.py
│   │   │   ├── event_monitor_task.py
│   │   │   ├── news_sync_task.py
│   │   │   └── seed_causal_data.py
│   │   ├── integrations/
│   │   │   ├── oil_price_client.py
│   │   │   ├── gdelt_client.py
│   │   │   └── news_client.py
│   │   ├── services/
│   │   │   └── causal_service.py
│   │   └── agents/
│   │       ├── subagents/
│   │       │   └── causal.py       # Causal sub-agent
│   │       └── tools/
│   │           └── causal_tools.py
│   └── .venv/
└── frontend/                    # Vercel (deployed)
    └── dist/                    # Production build
```