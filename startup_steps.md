# EquityAI - Replication & Startup Guide

This document outlines the exact sequence of commands and steps executed to bring up the full **EquityAI** platform, seed the database, run the ETL pipelines, and start the user interface.

---

## 📋 Summary of Running Services

| Component | Host / Port | Working Directory | Command / Process |
| :--- | :--- | :--- | :--- |
| **Colima (Docker Daemon)** | VM | `~` | `colima start` |
| **Docker Infrastructure** | `5432`, `6379`, `6333` | `majorproject/` | `docker-compose up -d` |
| **FastAPI Backend** | `http://localhost:8001` | `majorproject/backend-ai/` | `source .venv/bin/activate && python -m uvicorn src.main:app --port 8001 --reload` |
| **React Frontend** | `http://localhost:5173` | `majorproject/frontend/` | `npm run dev` |

---

## ⚡ Execution Steps

### Step 1: Initialize Docker Daemon (Colima)
If Docker is not running natively on macOS, Colima is used as the container runtime:
```bash
# Execute from any directory
colima start
```

### Step 2: Spin up Infrastructure Containers
Start **PostgreSQL**, **Redis**, and **Qdrant** in detached mode:
```bash
cd /Users/ashutoshkumar/MyWork/majorproject
docker-compose up -d
```

### Step 3: Run Database Migrations & Initial Seed Data
Populate the PostgreSQL tables with the default company entities, test users, and stock-specific metrics:
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai

# Activate Python Virtual Environment
source .venv/bin/activate

# Seed initial companies, users, and financial statements
python scripts/seed_db.py
```

### Step 4: Run ETL & Causal Intelligence Pipelines
Sync commodity price indexes, download relevant geopolitical triggers from GDELT, and populate news sentiment classifications:
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate

# Run full ETL and causal updates
python scripts/update_daily_data.py
```

### Step 5: Start the FastAPI Backend Server
Boot the web server that serves Iris's agent endpoints and data proxies:
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate

# Run Uvicorn dev server
python -m uvicorn src.main:app --port 8001 --reload
```

### Step 6: Start the React Frontend Application
Launch the dev server hosting the user interface:
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/frontend

# Launch Vite Dev Server
npm run dev
```
*Open `http://localhost:5173/` in your browser and switch the toggle to **Live Mode** in the sidebar.*

---

## 🔍 Verification
To verify that all components are correctly integrated and communication layers are active:
```bash
cd /Users/ashutoshkumar/MyWork/majorproject/backend-ai
source .venv/bin/activate

# Run End-to-End Suite
python test_e2e_full_flow.py
```
This script checks text normalization, LLM enrichment, Qdrant loads, causal chain parsing, portfolio calculations, and Iris chat agent invocation.
