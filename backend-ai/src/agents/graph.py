"""Native LangGraph research pipeline.

A single ``StateGraph`` models the whole chat research flow:

    START ─► plan ─►(Send fan-out)─► gather (parallel workers) ─► synthesize ─► END

- ``plan`` classifies intent (LLM, keyword fallback) into evidence tasks.
- ``gather`` runs each task in parallel via the Send API; results merge through an
  ``operator.add`` reducer.
- ``synthesize`` writes the grounded answer; its tokens stream via ``messages`` mode.
- Progress is emitted as ``custom`` stream events (``get_stream_writer``).

The graph is compiled with the Postgres checkpointer so sessions persist. The
planner/worker/aggregator logic is reused from ``research_pipeline`` (the proven
evidence tools) — this module is the orchestration, natively in LangGraph.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional
from uuid import UUID

from typing_extensions import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

_graph = None


class ResearchState(TypedDict, total=False):
    # inputs
    query: str
    user_id: str
    company_id: Optional[str]
    upload_id: Optional[str]
    portfolio_id: Optional[str]
    context_note: Optional[str]
    # working / outputs
    tasks: list[dict]
    evidence: Annotated[list[dict], operator.add]
    response: str
    sources: list[dict]


def _uuid(value: Optional[str]) -> Optional[UUID]:
    return UUID(value) if value else None


def _plan(state: ResearchState) -> dict:
    """Classify the query into a bounded set of evidence tasks."""
    from src.domains.chat.research_pipeline import ResearchPlanner

    writer = get_stream_writer()
    writer({"stage": "planning", "detail": "Planning research tasks"})

    tasks = ResearchPlanner().plan(
        query=state["query"],
        user_id=_uuid(state.get("user_id")),
        company_id=_uuid(state.get("company_id")),
        upload_id=_uuid(state.get("upload_id")),
        primary_portfolio_id=_uuid(state.get("portfolio_id")),
    )
    task_dicts = [{"name": t.name, "kind": t.kind, "params": t.params} for t in tasks]
    writer({"stage": "evidence", "detail": "Gathering evidence", "tasks": [t["kind"] for t in task_dicts]})
    return {"tasks": task_dicts}


def _route_to_workers(state: ResearchState) -> list[Send]:
    """Fan out: one parallel ``gather`` branch per planned task."""
    return [Send("gather", {"task": task}) for task in state.get("tasks", [])]


def _gather(payload: dict) -> dict:
    """Run one evidence task (reuses the proven worker tools)."""
    from src.domains.chat.research_pipeline import PlannedTask, ResearchWorkerPool

    task = payload["task"]
    writer = get_stream_writer()
    writer({"stage": "evidence_item", "detail": task.get("name", task.get("kind", ""))})

    planned = PlannedTask(name=task["name"], kind=task["kind"], params=task["params"])
    result = ResearchWorkerPool(1)._execute_task(planned)
    return {
        "evidence": [
            {"name": result.name, "kind": result.kind, "payload": result.payload, "source": result.source}
        ]
    }


def _synthesize(state: ResearchState) -> dict:
    """Write the grounded answer from gathered evidence (tokens stream)."""
    from langchain_core.messages import HumanMessage

    from src.domains.chat.research_pipeline import PlannedTask, ResultAggregator, TaskResult
    from src.llm import get_llm

    writer = get_stream_writer()
    writer({"stage": "synthesizing", "detail": "Writing answer"})

    tasks = [PlannedTask(t["name"], t["kind"], t["params"]) for t in state.get("tasks", [])]
    results = [TaskResult(e["name"], e["kind"], e["payload"], e["source"]) for e in state.get("evidence", [])]

    aggregator = ResultAggregator()
    prompt = aggregator.build_prompt_with_context(
        query=state["query"], tasks=tasks, results=results, context_note=state.get("context_note")
    )

    # Stream inside the node so ``messages`` mode captures per-token chunks,
    # while we accumulate the full text for persistence.
    llm = get_llm(temperature=0.3)
    parts: list[str] = []
    for chunk in llm.stream([HumanMessage(content=prompt)]):
        if chunk.content:
            parts.append(chunk.content)
    return {"response": "".join(parts), "sources": aggregator.build_sources(results)}


def build_research_graph():
    """Build (once) and return the compiled research StateGraph."""
    global _graph
    if _graph is not None:
        return _graph

    from src.agents.memory import get_memory_config

    builder = StateGraph(ResearchState)
    builder.add_node("plan", _plan)
    builder.add_node("gather", _gather)
    builder.add_node("synthesize", _synthesize)

    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", _route_to_workers, ["gather"])
    builder.add_edge("gather", "synthesize")
    builder.add_edge("synthesize", END)

    cfg = get_memory_config()
    _graph = builder.compile(checkpointer=cfg.get("checkpointer"), store=cfg.get("store"))
    print("[GRAPH] Compiled native LangGraph research pipeline")
    return _graph


def run_research(inputs: dict, config: dict) -> dict:
    """Blocking run — returns the final ``{response, sources}``."""
    final = build_research_graph().invoke(inputs, config)
    return {"response": final.get("response", ""), "sources": final.get("sources", [])}


def stream_research(inputs: dict, config: dict):
    """Yield ``("stage", dict)`` and ``("token", str)`` events from the graph.

    Only the synthesize node's tokens are surfaced (the planner/causal LLM calls
    run in other nodes and are filtered out).
    """
    graph = build_research_graph()
    for mode, data in graph.stream(inputs, config, stream_mode=["custom", "messages"]):
        if mode == "custom":
            yield ("stage", data)
        elif mode == "messages":
            chunk, meta = data
            if meta.get("langgraph_node") == "synthesize":
                text = getattr(chunk, "content", None)
                if text:
                    yield ("token", text)


def stream_prompt(prompt: str, config: dict):
    """Stream a direct LLM answer for a pre-built prompt (e.g. dashboard
    suggestions), yielding token strings. No evidence pipeline."""
    from langchain_core.messages import HumanMessage

    from src.llm import get_llm

    for chunk in get_llm(temperature=0.3).stream([HumanMessage(content=prompt)]):
        if chunk.content:
            yield chunk.content
