"""Orchestrator: builds the main LangGraph agent with sub-agents and memory
for equity research. No deepagents dependency — all LangGraph-native.

Architecture:
  agent node → routes to tools or sub_agent node based on tool call
  tools node → executes regular tools (resolve_company, internet_search, memory)
  sub_agent node → runs the requested sub-agent graph inline
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState

from src.agents.prompts.orchestrator import ORCHESTRATOR_PROMPT
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.web_search import internet_search
from src.agents.tools.orchestrator_tools import (
    memory_read, memory_write, read_skill, task_subagent,
)
from src.llm import get_llm

_agent = None
_memory_cfg: dict[str, Any] | None = None


def _tools_node(state: MessagesState) -> dict:
    """Execute tools and ensure all ToolMessages have non-null string content."""
    from langchain_core.messages import ToolMessage
    from langgraph.prebuilt import ToolNode as _ToolNode

    result = _ToolNode([
        resolve_company, internet_search, memory_read, memory_write, read_skill,
    ]).invoke(state)

    msgs = result.get("messages", [])
    safe_msgs = []
    for msg in msgs:
        if isinstance(msg, ToolMessage):
            content = msg.content
            if content is None:
                content = "[no data]"
            elif isinstance(content, list):
                content = str(content) if content else "[no data]"
            elif content == "":
                content = "[no data]"
            if content != msg.content:
                msg = ToolMessage(content=str(content), tool_call_id=msg.tool_call_id)
        safe_msgs.append(msg)
    return {"messages": safe_msgs}


def _agent_node_factory(llm, tools, system_msg: SystemMessage):
    """Build the agent node function (closure over LLM + tools + system prompt)."""
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: MessagesState) -> dict:
        msgs = [system_msg] + list(state["messages"])
        response = llm_with_tools.invoke(msgs)
        return {"messages": [response]}

    return agent_node


def _sub_agent_node(state: MessagesState) -> dict:
    """Execute a sub-agent task and return its result as a message.

    Called when the last message contains a task_subagent tool call.
    """
    messages = state["messages"]
    last_msg = messages[-1]

    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return {"messages": messages}

    # Execute each task_subagent call in sequence
    new_messages = list(messages)
    for tc in last_msg.tool_calls:
        if tc.get("name") != "task_subagent":
            continue

        args = tc.get("args", {})
        name = args.get("name", "")
        task = args.get("task", "")

        result = task_subagent(name, task)

        from langchain_core.messages import ToolMessage
        new_messages.append(ToolMessage(
            content=result,
            tool_call_id=tc.get("id", ""),
        ))

    return {"messages": new_messages}


def _route_after_agent(state: MessagesState) -> str:
    """Conditional edge routing after the agent node.

    If the agent called task_subagent → go to sub_agent node.
    If the agent called any other tool → go to tools node.
    Otherwise → END.
    """
    messages = state["messages"]
    last_msg = messages[-1]

    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        tool_names = [tc.get("name", "") for tc in last_msg.tool_calls]

        if "task_subagent" in tool_names:
            return "sub_agent"

        return "tools"

    return "end"


def build_research_agent():
    """Build and return the compiled orchestrator LangGraph agent.

    The orchestrator has tools for:
    - resolve_company: company name/ticker → UUID
    - internet_search: web search augmentation
    - memory_read / memory_write: persistent long-term memory
    - read_skill: domain knowledge progressive disclosure
    - task_subagent: delegate to specialist sub-agents

    Sub-agents are compiled as independent graphs and dispatched via task_subagent.
    The checkpointer provides conversation continuity within a session.
    """
    global _agent
    if _agent is not None:
        return _agent

    global _memory_cfg
    from src.agents.memory import get_memory_config
    _memory_cfg = get_memory_config()

    llm = get_llm()

    # Orchestrator tools (excluding task_subagent for the main ToolNode)
    regular_tools = [resolve_company, internet_search, memory_read, memory_write, read_skill]
    all_tools = regular_tools + [task_subagent]

    system_msg = SystemMessage(content=ORCHESTRATOR_PROMPT)

    graph = StateGraph(MessagesState)

    # Nodes — use safe wrappers that pad empty tool results
    graph.add_node("agent", _agent_node_factory(llm, all_tools, system_msg))
    graph.add_node("tools", _tools_node)
    graph.add_node("sub_agent", _sub_agent_node)

    # Edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"tools": "tools", "sub_agent": "sub_agent", "end": END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("sub_agent", "agent")

    _agent = graph.compile(checkpointer=_memory_cfg["checkpointer"])
    return _agent
