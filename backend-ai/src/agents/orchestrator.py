"""Orchestrator: builds the main deep agent with sub-agents, skills, and
long-term memory for equity research."""

from __future__ import annotations

from typing import Any

from deepagents import create_deep_agent

from src.agents.memory import get_memory_config
from src.agents.prompts.orchestrator import ORCHESTRATOR_PROMPT
from src.agents.subagents import get_all_subagents
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.web_search import internet_search
from src.config import get_settings

_agent = None


def _get_model_string() -> str:
    """Map ``src.config`` settings to the ``provider:model`` format expected by
    ``create_deep_agent``."""
    s = get_settings()
    model = s.get_llm_model()

    if s.llm_provider == "ollama":
        return f"ollama:{model}"
    if s.llm_provider == "openai":
        return f"openai:{model}"
    if s.llm_provider == "groq":
        return f"openai:{model}"
    if s.llm_provider == "deepseek":
        return f"openai:{model}"
    if s.llm_provider == "claude":
        return f"anthropic:{model}"
    return f"ollama:{model}"


def _get_model_kwargs() -> dict[str, Any]:
    """Return extra keyword arguments needed for providers that require custom
    base URLs or API keys (Groq, DeepSeek) beyond what the ``provider:model``
    string provides."""
    s = get_settings()
    kwargs: dict[str, Any] = {}

    if s.llm_provider == "groq":
        from src.agents.middleware_groq import GroqChatOpenAI

        kwargs["model"] = GroqChatOpenAI(
            model=s.get_llm_model(),
            api_key=s.groq_api_key or "",
            base_url=s.groq_base_url,
            temperature=s.llm_temperature,
            request_timeout=s.groq_timeout,
        )
    elif s.llm_provider == "deepseek":
        from src.agents.middleware_openai_compat import StrictOpenAICompatChatOpenAI

        kwargs["model"] = StrictOpenAICompatChatOpenAI(
            model=s.get_llm_model(),
            api_key=s.deepseek_api_key or "",
            base_url=s.deepseek_base_url,
            temperature=s.llm_temperature,
            request_timeout=s.deepseek_timeout,
        )
    elif s.llm_provider == "claude":
        from langchain_anthropic import ChatAnthropic

        kwargs["model"] = ChatAnthropic(
            model=s.get_llm_model(),
            api_key=s.anthropic_api_key or "",
            temperature=s.llm_temperature,
        )

    return kwargs


def build_research_agent():
    """Build and return the compiled orchestrator deep agent.

    The orchestrator has two lightweight tools (``resolve_company`` and
    ``internet_search``), delegates heavy analysis to five specialist
    sub-agents, and is equipped with:
    - **Long-term memory** via CompositeBackend (/memories/ persists across sessions)
    - **Skills** (progressive disclosure) for Indian equity, annual-report,
      and portfolio-strategy domain knowledge
    - **Checkpointer** for conversation continuity within a session
    """
    print(f"[ORCHESTRATOR] build_research_agent() called")
    
    global _agent
    if _agent is not None:
        print(f"[ORCHESTRATOR] Returning cached agent instance")
        return _agent

    print(f"[ORCHESTRATOR] Building new research agent...")
    print(f"[ORCHESTRATOR] Model string: {_get_model_string()}")

    extra = _get_model_kwargs()

    if "model" in extra:
        model = extra.pop("model")
    else:
        model = _get_model_string()

    print(f"[ORCHESTRATOR] Model configured: {model}")
        
    memory_cfg = get_memory_config()
    
    print(f"[ORCHESTRATOR] Memory config keys: {list(memory_cfg.keys())}")
    print(f"[ORCHESTRATOR] System prompt (first 500 chars): {ORCHESTRATOR_PROMPT[:500]}...")
    
    subagents = get_all_subagents()
    print(f"[ORCHESTRATOR] Subagents: {list(subagents.keys()) if hasattr(subagents, 'keys') else subagents}")
    print(f"[ORCHESTRATOR] Tools: resolve_company, internet_search")

    print(f"[ORCHESTRATOR] Calling create_deep_agent...")
    _agent = create_deep_agent(
        model=model,
        tools=[resolve_company, internet_search],
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents=subagents,
        **memory_cfg,
    )

    print(f"[ORCHESTRATOR] Agent built successfully!")
    print(f"[ORCHESTRATOR] Agent type: {type(_agent)}")
    return _agent
