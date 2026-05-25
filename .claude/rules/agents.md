# Subsystem: Agents

## Framework
- Uses **DeepAgents** + **LangGraph**
- Multi-agent directed graph routing for complex thematic processing.

## Agent Orchestration
1. **Iris** is the primary orchestrator that tracks sessions, contextual constraints, and manages delegation.
2. **Specialists** have focused capabilities and specific tool access boundaries:
   - **Company Analyst**: Individual stock deeply analytical tasks.
   - **Comparison Analyst**: Peer comparison and competitor analysis.
   - **Portfolio Manager**: Beta, Sharpe, volatility analysis over an active holdings list.
   - **News Analyst**: Tracks recent filings, market sentiment.
   - **Document Reader**: Processes deeply into indexed documents with vector search.
   - **Theme Explorer**: Semantic and vector queries across macroeconomic topics.
   - **Causal Detective**: Predictive tracking and domino-effect logic analysis (11 causal chains).