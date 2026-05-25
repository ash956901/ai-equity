# Subsystem: Architecture Context and Progress

## Tech Stack
- **LLM**: NVIDIA NIM `gpt-oss-120b`
- **Embeddings**: Ollama `nomic-embed-text`
- **Vector DB**: Qdrant (self-hosted)
- **Agent Framework**: DeepAgents + LangGraph
- **Market Data**: FMP API + scraper fallback
- **Auth**: UUID in localStorage (demo scale; note JWT needed for full production)

## Project Status (as of latest check)
Current overall completion is roughly 80%.
- **Phase 1 (ETL)**: 100% complete (All 10 capabilities verified).
- **Phase 2 (AI/Agents)**: 100% complete (Orchestrator + 6 specialists live).
- **Phase 3 (Backend API)**: ~95% complete (21 working endpoints).
- **Phase 4 (Frontend)**: Work-in-Progress (10 views built, wiring gaps remaining).

## Agent Architecture
- **Iris**: Orchestrator agent that acts as system entry point. Main maintainer of user context, memory, and delegates.
- **7 Specialist Agents**: Under Iris's control (e.g., Company Analyst, Comparison Analyst, Portfolio Manager, Theme Explorer, News Analyst, Document Reader, Causal Detective).