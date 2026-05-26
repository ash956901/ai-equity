"""Orchestrator tools: memory + sub-agent dispatch.

No deepagents dependency — all LangGraph-native.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.memory import get_memory_config
from src.config import get_settings

logger = logging.getLogger(__name__)

# Sub-agent registry: built lazily
_subagent_graphs: dict[str, Any] | None = None


def _get_subagent_graphs() -> dict[str, Any]:
    """Lazy-load sub-agent graphs on first use."""
    global _subagent_graphs
    if _subagent_graphs is not None:
        return _subagent_graphs

    from src.agents.subagents import get_all_subagents

    _subagent_graphs = {}
    for spec in get_all_subagents():
        graph = _build_subagent_graph(spec)
        _subagent_graphs[spec["name"]] = graph
        logger.debug("Compiled sub-agent graph: %s", spec["name"])

    return _subagent_graphs


def _build_subagent_graph(spec: dict) -> Any:
    """Build a LangGraph agent for a single sub-agent.

    Each sub-agent gets its own 2-node graph (agent + tools).
    The system prompt + user task go in as messages, tools are bound to LLM.
    Empty tool results are padded to "" to satisfy strict model APIs.
    """
    from langgraph.graph import StateGraph, END, START
    from langgraph.graph.message import MessagesState
    from langgraph.prebuilt import tools_condition
    from langgraph.prebuilt.tool_node import ToolNode
    from langchain_core.messages import ToolMessage
    from src.llm import get_llm

    llm = get_llm()
    tools = spec["tools"]

    def sub_agent_node(state: MessagesState) -> dict:
        """Run the sub-agent LLM call with tools."""
        msgs = [SystemMessage(content=spec["system_prompt"])] + list(state["messages"])
        response = llm.bind_tools(tools).invoke(msgs)
        return {"messages": state["messages"] + [response]}

    def safe_tools_node(state: MessagesState) -> dict:
        """Execute tools and ensure all ToolMessages have non-null string content.

        Groq's gpt-oss models reject null/empty/list content in tool messages.
        """
        from langgraph.prebuilt import ToolNode as _ToolNode
        result = _ToolNode(tools).invoke(state)
        msgs = result.get("messages", [])
        safe_msgs = []
        for msg in msgs:
            if isinstance(msg, ToolMessage):
                content = msg.content
                if content is None:
                    content = "[no data]"
                elif isinstance(content, list):
                    content = json.dumps(content) if content else "[no data]"
                elif content == "":
                    content = "[no data]"
                if content != msg.content:
                    msg = ToolMessage(content=str(content), tool_call_id=msg.tool_call_id)
            safe_msgs.append(msg)
        return {"messages": safe_msgs}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", sub_agent_node)
    graph.add_node("tools", safe_tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def memory_read(path: str) -> str:
    """Read a file from the persistent memory store.

    Reads from the /memories/ directory. Use for user_preferences.txt,
    watchlist.txt, or research_notes/<topic>.txt.

    Args:
        path: Relative path within memories (e.g., "user_preferences.txt")
    """
    cfg = get_memory_config()
    filepath = Path(cfg["memories_dir"]) / path

    try:
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return f"File not found: {path}"
    except Exception as e:
        return f"Error reading {path}: {e}"


def memory_write(path: str, content: str) -> str:
    """Write a file to the persistent memory store.

    Writes to the /memories/ directory. All parent directories are created
    automatically. Use for saving user preferences, watchlist, or research notes.

    Args:
        path: Relative path within memories (e.g., "user_preferences.txt")
        content: Text content to write
    """
    cfg = get_memory_config()
    filepath = Path(cfg["memories_dir"]) / path
    filepath.parent.mkdir(parents=True, exist_ok=True)

    try:
        filepath.write_text(content, encoding="utf-8")
        return f"Written to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


def read_skill(skill_name: str) -> str:
    """Read a skill file to get domain-specific guidance.

    Args:
        skill_name: Name of skill directory (e.g., "indian-equity-analysis")
    """
    cfg = get_memory_config()
    filepath = Path(cfg["skills_dir"]) / skill_name / "SKILL.md"

    try:
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return f"Skill not found: {skill_name}"
    except Exception as e:
        return f"Error reading skill {skill_name}: {e}"


def task_subagent(name: str, task: str) -> str:
    """Delegate work to a specialized sub-agent and return its result.

    Available sub-agents:
    - company-analysis: deep-dive financials, ratios, risk flags, filings, news
    - comparison: side-by-side benchmarking of 2-5 companies (returns JSON)
    - portfolio: holdings, allocation, concentration, risk, news
    - news-sentiment: news aggregation and sentiment analysis
    - causal: hidden patterns - world events → commodities → sectors → stocks
    - doc-insight: document analysis (PDF/PPT/annual report) with page citations
    - thematic-discovery: find companies matching a theme or topic

    Args:
        name: Sub-agent name (must match exactly)
        task: The task/question to ask the sub-agent
    """
    graphs = _get_subagent_graphs()

    if name not in graphs:
        available = ", ".join(graphs.keys())
        return f"Unknown sub-agent '{name}'. Available: {available}"

    try:
        result = graphs[name].invoke(
            {"messages": [HumanMessage(content=task)]},
            config={"recursion_limit": 15},
        )
        last_msg = result["messages"][-1]
        return last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    except Exception as e:
        logger.exception("Sub-agent %s failed", name)
        return f"Sub-agent '{name}' failed: {e}"
