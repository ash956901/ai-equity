# Presentation Cheat Sheet: Data & Services

This document contains quick-reference commands to demonstrate the platform's backend services, databases, and background workers during your presentation.

---

## 1. Relational Database (PostgreSQL)

Use these commands to drop into the database and prove that the ETL pipelines and Causal Intelligence engines are actively storing data.

**Connect to the Database Container:**
```bash
docker-compose exec postgres psql -U postgres -d equity_research
```

**Useful SQL Commands (run these inside the `equity_research=#` prompt):**

*   **List all tables:**
    ```sql
    \dt
    ```
*   **Show actual financial ratios stored for companies:**
    ```sql
    SELECT c.ticker_nse, r.period_end, r.pe_ratio, r.roe, r.debt_to_equity 
    FROM financial_ratios r 
    JOIN companies c ON r.company_id = c.id 
    ORDER BY r.period_end DESC LIMIT 5;
    ```
*   **Show raw financial statement line items (e.g., Revenue & Profit):**
    ```sql
    SELECT c.ticker_nse, f.statement_type, f.period_end, f.line_item, f.value, f.unit
    FROM financial_statements_raw f
    JOIN companies c ON f.company_id = c.id
    WHERE f.line_item ILIKE '%revenue%' OR f.line_item ILIKE '%profit%'
    ORDER BY f.period_end DESC LIMIT 5;
    ```
*   **Show recent volatile commodities:**
    ```sql
    SELECT symbol, name, price, change_pct FROM commodity_prices ORDER BY timestamp DESC LIMIT 5;
    ```
*   **Show recent geopolitical events:**
    ```sql
    SELECT title, country, category, confidence FROM geopolitical_events ORDER BY event_date DESC LIMIT 5;
    ```
*   **Show tracked causal chains:**
    ```sql
    SELECT name, trigger_value, confidence FROM causal_chains;
    ```
*   **Prove the ETL background jobs are running (shows run history):**
    ```sql
    SELECT pipeline_name, status, records_processed, duration_seconds FROM etl_runs ORDER BY started_at DESC LIMIT 5;
    ```
*(Type `\q` and press Enter to exit the postgres prompt).*

---

## 2. Vector Database (Qdrant)

Use these commands to prove that document embeddings (RAG) are working and data is loaded.

**Option A: Quick cURL Check**
Show the collection details and total vector count:
```bash
curl http://localhost:6333/collections/company_filings
```
Show a sample vector and its metadata payload:
```bash
curl -X POST http://localhost:6333/collections/company_filings/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 1, "with_payload": true, "with_vector": true}'
```

**Option B: Python Verification Script**
Run this from the `backend-ai/` directory:
```bash
cd backend-ai
source .venv/bin/activate
python -c "
from src.services.vector_service import VectorService
svc = VectorService()
client = svc._get_client()
count = client.count(collection_name='company_filings')
print(f'✅ Total Document Chunks in Qdrant: {count.count}')
"
```

---

## 3. Background Workers (Celery & Beat)

Celery is the engine that runs all the web scrapers, document parsers, and sync tasks. 

**Terminal 1: Start the Celery Worker (Executes the Jobs)**
*Tip: Keep this terminal visible when you trigger an action in the UI so the audience can see the real-time logs of documents being parsed.*
```bash
cd backend-ai
source .venv/bin/activate
celery -A src.celery_app worker --loglevel=info
```

**Terminal 2: Start Celery Beat (The Scheduler)**
*This acts like a cron job, automatically triggering the commodity/news syncs at their defined intervals.*
```bash
cd backend-ai
source .venv/bin/activate
celery -A src.celery_app beat --loglevel=info
```

*(Alternatively, run them both in one terminal: `celery -A src.celery_app worker --beat --loglevel=info`)*

---

## 4. Live API Demonstrations

If someone asks to see the "Hidden Patterns" or Causal Intelligence working under the hood without using the UI, you can run these directly from the terminal.

**Show currently detected Market Hidden Patterns:**
```bash
cd backend-ai
source .venv/bin/activate
python -c "
import json
from src.agents.tools.causal_tools import get_market_hidden_patterns
print(json.dumps(get_market_hidden_patterns(), indent=2))
"
```

**Test the Causal Sub-Agent Routing:**
```bash
curl -X POST "http://localhost:8001/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "query": "Are there any hidden risks or non-obvious patterns affecting the Indian market right now based on global events?",
    "expertise_level": "advanced"
  }'
```