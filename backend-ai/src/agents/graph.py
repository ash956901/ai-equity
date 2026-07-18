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


MAX_AGENT_STEPS = 4

AGENT_SYSTEM_PROMPT = (
    "You are a senior Indian-equity research analyst coordinating specialist tools. "
    "For the user's request, decide which specialists to call and in what order, using "
    "their results to inform the next call. Call `causal_analysis` for hidden/second-order "
    "impacts, `portfolio_analysis` for the user's holdings, `compare_companies` for peer "
    "comparisons, `company_analysis`/`news_analysis`/`document_analysis` for single names, "
    "and `thematic_discovery` for themes. Only assert facts returned by the tools; never "
    "invent tickers or numbers. Stop calling tools once you have enough to answer."
)


class ResearchState(TypedDict, total=False):
    # inputs
    query: str
    user_id: str
    company_id: Optional[str]
    upload_id: Optional[str]
    portfolio_id: Optional[str]
    context_note: Optional[str]
    # working / outputs
    route: str
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


def _router(state: ResearchState) -> dict:
    """Classify the query as 'simple' (fast workflow) or 'complex' (agent loop)."""
    from langchain_core.messages import HumanMessage

    from src.llm import get_llm

    writer = get_stream_writer()
    query = state["query"]
    route = "simple"
    try:
        prompt = (
            "Classify this equity-research query as 'simple' or 'complex'.\n"
            "simple = a direct lookup: one metric/fact, a single company, a definition, "
            "one news or causal fact.\n"
            "complex = needs multi-step reasoning, judgement, or several domains: "
            "recommendations, 'should I', portfolio rebalancing, multi-company comparison "
            "with a verdict, open-ended strategy.\n"
            f"Query: {query}\n"
            "Reply with ONLY one word: simple or complex."
        )
        answer = get_llm(temperature=0.0).invoke([HumanMessage(content=prompt)]).content.lower()
        route = "complex" if "complex" in answer else "simple"
    except Exception:
        ql = query.lower()
        route = "complex" if any(
            k in ql for k in ("should i", "rebalance", "recommend", "strategy", " vs ",
                              "versus", "compare", "better", "given the", "allocate")
        ) else "simple"
    writer({"stage": "routing", "detail": f"route={route}"})
    return {"route": route}


def _route_decision(state: ResearchState) -> str:
    return "agent" if state.get("route") == "complex" else "plan"


def _agent(state: ResearchState) -> dict:
    """Bounded ReAct loop: the LLM dynamically calls specialist tools, using each
    result to decide the next, until it has enough. Returns gathered evidence
    (the shared ``synthesize`` node writes the streamed answer)."""
    import json

    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    from src.agents.specialists import SPECIALIST_TOOLS, SPECIALISTS_BY_NAME
    from src.llm import get_llm

    writer = get_stream_writer()
    writer({"stage": "reasoning", "detail": "Coordinating specialist agents"})

    llm = get_llm(temperature=0.2).bind_tools(SPECIALIST_TOOLS)
    tool_config = {"configurable": {"user_id": state.get("user_id"), "portfolio_id": state.get("portfolio_id")}}

    context = state["query"]
    if state.get("context_note"):
        context += f"\n\n[Context: {state['context_note']}]"
    messages: list = [SystemMessage(content=AGENT_SYSTEM_PROMPT), HumanMessage(content=context)]

    evidence: list[dict] = []
    for _ in range(MAX_AGENT_STEPS):
        ai = llm.invoke(messages)
        messages.append(ai)
        tool_calls = getattr(ai, "tool_calls", None) or []
        if not tool_calls:
            break
        for call in tool_calls:
            name = call["name"]
            writer({"stage": "specialist", "detail": name})
            specialist = SPECIALISTS_BY_NAME.get(name)
            if specialist is None:
                result: Any = {"error": f"unknown specialist {name}"}
            else:
                try:
                    result = specialist.invoke(call["args"], config=tool_config)
                except Exception as exc:
                    result = {"error": str(exc)}
            evidence.append(
                {
                    "name": name,
                    "kind": "specialist",
                    "payload": result,
                    "source": {"name": name, "kind": "specialist", "status": "ok"},
                }
            )
            messages.append(
                ToolMessage(content=json.dumps(result, default=str)[:6000], tool_call_id=call["id"])
            )

    return {"evidence": evidence}


def build_research_graph():
    """Build (once) and return the compiled research StateGraph."""
    global _graph
    if _graph is not None:
        return _graph

    from src.agents.memory import get_memory_config

    builder = StateGraph(ResearchState)
    builder.add_node("router", _router)
    builder.add_node("plan", _plan)
    builder.add_node("gather", _gather)
    builder.add_node("agent", _agent)
    builder.add_node("synthesize", _synthesize)

    builder.add_edge(START, "router")
    builder.add_conditional_edges("router", _route_decision, ["plan", "agent"])
    builder.add_conditional_edges("plan", _route_to_workers, ["gather"])
    builder.add_edge("gather", "synthesize")
    builder.add_edge("agent", "synthesize")
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
