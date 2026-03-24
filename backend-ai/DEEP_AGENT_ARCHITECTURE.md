# AI Equity Research Platform - Deep Multi-Agent Backend Architecture

## 1) High-level architecture

This implementation introduces a production-oriented, backend-only, deep-agent system built around a LangGraph orchestrator.

Data flow:

User/CLI -> ResearchOrchestratorAgent -> Specialist Deep Agents -> Tool Layer -> Agent Outputs -> Orchestrator Synthesis -> Structured Final Output

Key architectural properties:

- Deep agents with memory + state + reasoning loops
- LangGraph DAG-based orchestration with dynamic plan routing
- RAG-oriented retrieval path (`RetrievalAgent` + embedding/vector tools)
- Hybrid semantic + numerical analysis (`RetrievalAgent` + `FinancialAnalysisAgent` + `PortfolioAgent`)
- File-system observability for each run (`workflow_runs/...`)
- Pluggable tools and model/provider abstraction via config and env vars

## 2) What already existed vs what was added

### Already implemented in repository

- Existing LangGraph workflow and specialist agents in [src/agents](src/agents)
- Vector service integration with Qdrant in [src/services/vector_service.py](src/services/vector_service.py)
- Baseline tool modules in [src/tools](src/tools)
- LLM provider abstraction in [src/llm/__init__.py](src/llm/__init__.py)

### Added in this implementation

- Deep orchestrator package: [src/deep_research](src/deep_research)
- New master agent: `ResearchOrchestratorAgent`
- Deep specialist agents:
  - `RetrievalAgent`
  - `DocumentIntelligenceAgent`
  - `FinancialAnalysisAgent`
  - `ComparisonAgent`
  - `PortfolioAgent`
  - `ReportGenerationAgent`
  - `WebSearchAgent`
- End-to-end run observability with required artifacts:
  - `user_input.json`
  - `orchestrator_plan.json`
  - `agent_calls.log`
  - `tool_calls.log`
  - `intermediate_outputs/*.json`
  - `final_output.json`
- Fully interactive CLI entrypoint: [run_research_orchestrator.py](run_research_orchestrator.py)

## 3) Folder structure

- [src/deep_research/__init__.py](src/deep_research/__init__.py)
- [src/deep_research/state.py](src/deep_research/state.py)
- [src/deep_research/observability.py](src/deep_research/observability.py)
- [src/deep_research/tools.py](src/deep_research/tools.py)
- [src/deep_research/agents.py](src/deep_research/agents.py)
- [src/deep_research/orchestrator.py](src/deep_research/orchestrator.py)
- [run_research_orchestrator.py](run_research_orchestrator.py)

## 4) Runtime behavior summary

1. CLI captures user intent dynamically (no workflow defaults).
2. `ResearchOrchestratorAgent` creates a per-run folder and writes `user_input.json`.
3. Orchestrator creates dynamic execution plan and writes `orchestrator_plan.json`.
4. LangGraph dispatcher executes specialist deep agents in plan order.
5. Each agent runs a reasoning loop and calls tools dynamically.
6. Tool calls and agent calls are logged to `tool_calls.log` and `agent_calls.log`.
7. Intermediate outputs are serialized in `intermediate_outputs/`.
8. Final structured result is emitted and saved to `final_output.json`.

## 5) CLI interaction model

Interactive prompts include:

- Query/objective
- Company names
- Document upload paths (PDF/PPT)
- URLs
- Analysis type
- Comparison option + company metrics
- Portfolio option + per-holding metrics
- Report generation toggle
- Web augmentation toggle
- Retrieval top-K

## 6) Environment variables

Added config keys:

- `WORKFLOW_RUNS_DIR`
- `DEEP_AGENT_MAX_STEPS`
- `TAVILY_API_KEY` (optional)

They are reflected in [src/config.py](src/config.py) and [.env.example](../.env.example).

## 7) Example run script

Run from `backend-ai` folder:

- `python run_research_orchestrator.py`

This starts an interactive multi-turn deep-agent session.

## 8) Extensibility

- Add new agent by implementing `DeepAgentBase` and wiring a node in [src/deep_research/orchestrator.py](src/deep_research/orchestrator.py)
- Add new tools in [src/deep_research/tools.py](src/deep_research/tools.py)
- Swap models via existing LLM/embedding config in [src/config.py](src/config.py)
