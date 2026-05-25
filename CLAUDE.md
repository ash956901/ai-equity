# AI Equity Research Platform - Claude Configuration

Welcome to the AI Equity Research Platform! This file provides high-level system context and rules for AI development on this codebase.

## 1. System Architecture Overview
This is a three-tier architecture:
1. **Data Gatherer (ETL System)**: A 24/7 data ingestion pipeline capturing filings, news, and market data.
2. **AI Brain (Agent Architecture)**: An orchestrated team of specialist agents (led by "Iris") that analyzes the ingested data.
3. **Hidden Pattern Finder (Causal Intelligence)**: A system tracking predictive domino-effects across sectors and commodities.

## 2. Using the Rules Directory
For detailed guidelines on specific subsystems, **you must read the relevant rule file** in the `.claude/rules/` directory before proceeding:
- `.claude/rules/context.md`: Overall tech stack and system state.
- `.claude/rules/etl_pipeline.md`: Data processing, chunking, embeddings, and Qdrant rules.
- `.claude/rules/agents.md`: LangGraph setup, Iris orchestrator, and specialist agent constraints.
- `.claude/rules/backend_api.md`: FastAPI conventions, Celery, and testing flows.
- `.claude/rules/frontend.md`: Vite/React app UI specs and API wiring.
- `.claude/rules/database.md`: Postgres relational schema and Qdrant vector database rules.

## 3. The Golden Rule: Use MEMORY.md
To prevent compounding mistakes or repeated discovery steps, **you must log all lessons learned, active rabbit holes, and resolved issues into `MEMORY.md`** at the completion of significant tasks or debugging sessions. 
Before starting a complex task, always check `MEMORY.md` to avoid repeating past mistakes.