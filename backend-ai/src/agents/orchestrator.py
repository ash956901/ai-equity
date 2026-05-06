"""Orchestrator: builds the main deep agent with tools and memory."""

from __future__ import annotations

from typing import Any

from deepagents import create_deep_agent

from src.agents.memory import get_memory_config
from src.agents.prompts.orchestrator import ORCHESTRATOR_PROMPT
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.web_search import internet_search
from src.agents.tools.financial import get_latest_financials, calculate_ratios
from src.agents.tools.news import get_recent_news
from src.agents.tools.causal_tools import get_causal_tools
from src.config import get_settings


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
    if s.llm_provider == "cerebras":
        return f"openai:{model}"
    if s.llm_provider == "nvidia":
        return f"openai:{model}"
    return f"ollama:{model}"


def _get_model_kwargs() -> dict[str, Any]:
    """Return extra keyword arguments needed for providers that require custom
    base URLs or API keys (Groq, DeepSeek, Cerebras) beyond what the ``provider:model``
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
        )
    elif s.llm_provider == "deepseek":
        from src.agents.middleware_openai_compat import StrictOpenAICompatChatOpenAI

        kwargs["model"] = StrictOpenAICompatChatOpenAI(
            model=s.get_llm_model(),
            api_key=s.deepseek_api_key or "",
            base_url=s.deepseek_base_url,
            temperature=s.llm_temperature,
        )
    elif s.llm_provider == "cerebras":
        from langchain_openai import ChatOpenAI

        kwargs["model"] = ChatOpenAI(
            model=s.get_llm_model(),
            api_key=s.cerebras_api_key or "",
            base_url=s.cerebras_base_url,
            temperature=s.llm_temperature,
        )
    elif s.llm_provider == "nvidia":
        from langchain_openai import ChatOpenAI

        kwargs["model"] = ChatOpenAI(
            model=s.get_llm_model(),
            api_key=s.deepseek_api_key or "",
            base_url=s.deepseek_base_url,
            temperature=s.llm_temperature,
        )

    return kwargs


def build_research_agent():
    """Build and return the compiled orchestrator deep agent without sub-agents."""
    print(f"[ORCHESTRATOR] Building new research agent...")
    
    model_str = _get_model_string()
    print(f"[ORCHESTRATOR] Model string: {model_str}")

    extra = _get_model_kwargs()

    if "model" in extra:
        model = extra.pop("model")
    else:
        model = model_str

    print(f"[ORCHESTRATOR] Model configured: {model}")
        
    memory_cfg = get_memory_config()
    
    causal_tools = get_causal_tools()
    all_tools = [
        resolve_company,
        internet_search,
        get_latest_financials,
        calculate_ratios,
        get_recent_news
    ] + causal_tools
    
    print(f"[ORCHESTRATOR] Tools configured: {[getattr(t, 'name', getattr(t, '__name__', str(t))) for t in all_tools]}")

    agent = create_deep_agent(
        model=model,
        tools=all_tools,
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents={},
        **memory_cfg,
    )

    print(f"[ORCHESTRATOR] Agent built successfully!")
    return agent

