# EquityAI - 1-Day Completion Plan

**Date:** 2026-04-26  
**Status:** URGENT - Single Day Delivery  
**Goal:** Make EquityAI production-ready and demo-able

---

## Executive Summary

This is a **ONE-DAY SPRINT** to complete EquityAI. Focus on:
1. **Fixing broken features** (not building new ones)
2. **Making existing code work** (not adding capabilities)
3. **Ensuring demo-ability** for presentation

**Success Definition:** All 11 views load without errors, chat works end-to-end with visible agent actions, authentication works, and core research features function.

---

## HOUR-BY-HOUR TIMELINE

| Hour | Task | Deliverable |
|------|------|-------------|
| **0:00-1:30** | Fix 3 broken API endpoints | Portfolio & News pages load |
| **1:30-3:00** | Implement JWT auth | Login/register works, tokens issued |
| **3:00-4:30** | Seed filings collection | RAG over earnings calls works |
| **4:30-6:00** | Add tool execution logs | Chat shows "Iris searched..." |
| **6:00-7:00** | Portfolio performance | Shows returns, gainers/losers |
| **7:00-8:00** | Alert evaluator | Alerts trigger and notify |
| **8:00-8:30** | Integration test | All 11 views verified |

---

## PHASE 1: Foundation (Hours 0-3)

### Task 1.1: Fix Broken API Endpoints (90 min)

**Problem:** 3 endpoints return 404

| Endpoint | Status | Fix Location |
|----------|--------|-------------|
| GET /api/v1/upstox/portfolio/holdings | 404 | src/external_apis/upstox/ |
| GET /api/v1/newsdata/market/headlines | 404 | src/external_apis/newsdata/ |
| GET /api/v1/newsdata/sentiment/{symbol} | 404 | src/external_apis/newsdata/ |

**Steps:**

1. Check router registration in src/app/routers.py
   - Add upstox_router and newsdata_router if missing

2. Fix Upstox client (src/external_apis/upstox/client.py)
   - Verify endpoint: https://api.upstox.com/v2/portfolio/short-term-positions
   - Add auth token refresh

3. Fix NewsData client (src/external_apis/newsdata/client.py)
   - Check API key in .env
   - Add fallback to RSS feeds

**Success Criteria:** All 3 endpoints return 200 OK

---

### Task 1.2: Implement JWT Authentication (90 min)

**Problem:** No login/register - demo mode only

**Implementation:**

1. Create auth module (src/domains/auth/)
   - router.py - Login, register endpoints
   - service.py - Password hashing, token generation
   - schemas.py - Pydantic models

2. Add to requirements.txt:
   ```
   python-jose[cryptography]>=3.3.0
   passlib[bcrypt]>=1.7.4
   python-multipart>=0.0.6
   ```

3. Create endpoints:
   - POST /auth/register
   - POST /auth/login

4. Register router in src/app/routers.py

5. Update frontend (frontend/src/shared/api/auth.ts)

**Success Criteria:** Can register, login, receive JWT

---

## PHASE 2: Core Features (Hours 3-6)

### Task 2.1: Seed Filings Collection (90 min)

**Problem:** Qdrant filings collection is empty

**Quick Fix:** Manual seeding (don't wait for ETL)

**Steps:**

1. Download 5 annual reports (TCS, Reliance, HDFCBANK, INFY, ICICIBANK)

2. Create seed script (backend-ai/scripts/seed_filings.py)

3. Run script:
   ```bash
   cd backend-ai
   python scripts/seed_filings.py
   ```

4. Verify in Qdrant:
   ```bash
   curl http://localhost:6333/collections/company_filings
   ```

**Success Criteria:** Qdrant shows 500+ vectors

---

### Task 2.2: Add Agent Tool Execution Logs (90 min)

**Problem:** Chat shows response but user cannot see what tools Iris used

**Implementation:**

1. Update chat service (src/domains/chat/service.py)
   - Add ToolCallCollector callback class
   - Capture tool_name, input, output, timestamp
   - Return tool_calls in response

2. Create tool_calls table (add migration)

3. Update frontend (frontend/src/pages/Chat/index.tsx)
   - Show expandable "Actions Taken" section
   - Display: "Iris searched filings for revenue growth (3 results)"

**Success Criteria:** Chat response includes visible tool execution logs

---

## PHASE 3: Polish (Hours 6-8)

### Task 3.1: Portfolio Performance Metrics (60 min)

**Problem:** Portfolio shows holdings but no returns

**Implementation:**

1. Add endpoint (src/domains/portfolio/router.py)
   - GET /{portfolio_id}/performance
   - Calculate: total_value, total_cost, total_return, return_pct
   - Calculate: day_change, day_change_pct
   - Calculate: top_gainers, top_losers

2. Update frontend to show performance cards

**Success Criteria:** Portfolio shows returns and metrics

---

### Task 3.2: Basic Alert Trigger Evaluator (60 min)

**Problem:** Alerts exist but never trigger

**Implementation:**

1. Create evaluator (src/domains/alerts/evaluator.py)
   - Evaluate price_above conditions
   - Evaluate price_below conditions
   - Create notifications on trigger

2. Add Celery task:
   ```python
   @app.task
   def evaluate_alerts():
       # Run every 5 minutes
       pass
   ```

**Success Criteria:** Alerts trigger when conditions met

---

## OUT OF SCOPE (Do NOT attempt)

These features are NOT built and would take days/weeks:

1. Theme Detection Agent - No automatic theme discovery
2. Vision Chart Extraction - Cannot extract data from charts
3. Table Extraction from PDFs - No automated parsing
4. True LangGraph State Machine - Using deepagents abstraction
5. Hybrid Search - Only vector, no keyword fallback
6. Full ETL Automation - Crawlers exist but not running
7. Real-time WebSocket Streaming - Polling only
8. Advanced RBAC - Basic auth only

---

## FILES TO EDIT

Backend:
- src/app/routers.py (add auth router)
- src/domains/auth/ (NEW: router.py, service.py, schemas.py)
- src/domains/chat/service.py (add tool logs)
- src/domains/portfolio/router.py (add performance)
- src/domains/alerts/evaluator.py (NEW)
- src/etl/tasks.py (add alert task)
- src/external_apis/upstox/client.py (fix holdings)
- src/external_apis/newsdata/client.py (fix news)
- scripts/seed_filings.py (NEW)
- requirements.txt (JWT deps)
- alembic/versions/ (tool_calls migration)

Frontend:
- src/shared/api/auth.ts (wire endpoints)
- src/pages/Chat/index.tsx (show tool calls)
- src/pages/Portfolio/index.tsx (show performance)

---

## SUCCESS CHECKLIST (End of Day)

- [ ] Can register new user
- [ ] Can login and receive JWT
- [ ] JWT works on all protected endpoints
- [ ] Portfolio holdings endpoint returns 200
- [ ] News headlines endpoint returns 200
- [ ] News sentiment endpoint returns 200
- [ ] Qdrant company_filings collection has 500+ vectors
- [ ] Chat response includes tool execution logs
- [ ] Portfolio shows total return and day change
- [ ] Alerts trigger when conditions met
- [ ] All 11 frontend views load without errors
- [ ] Integration test passes end-to-end

---

## RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| External APIs fail | Skip features, use demo data |
| Qdrant seeding takes too long | Seed only 2-3 companies |
| JWT implementation complex | Use simple PyJWT, skip refresh tokens |
| Time runs out | Cut portfolio performance, keep auth + tool logs |

---

## COMMANDS

```bash
# Install dependencies
cd backend-ai
pip install python-jose[cryptography] passlib[bcrypt] python-multipart

# Run migrations
alembic upgrade head

# Seed filings
python scripts/seed_filings.py

# Start backend
python -m uvicorn src.main:app --port 8001 --reload &

# Start frontend
cd ../frontend
npm run dev &

# Test
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","name":"Test User"}'
```

---

**This is aggressive but achievable. Focus on making broken things work.**
