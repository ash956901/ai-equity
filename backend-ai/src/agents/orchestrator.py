"""Orchestrator: builds the main deep agent with sub-agents, skills, and
long-term memory for equity research."""

from __future__ import annotations

from typing import Any

from deepagents import create_deep_agent

from src.app.telemetry import traceable
from src.agents.memory import get_memory_config
from src.agents.prompts.orchestrator import ORCHESTRATOR_PROMPT
from src.agents.subagents import get_all_subagents
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.web_search import internet_search
from src.config import get_settings

_agent = None
_agent_fallback = None
_react_agent = None
_react_agent_fallback = None


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


def _get_model_kwargs(use_fallback_key: bool = False) -> dict[str, Any]:
    """Return extra keyword arguments needed for providers that require custom
    base URLs or API keys (Groq, DeepSeek) beyond what the ``provider:model``
    string provides.

    When ``use_fallback_key`` is True and a second DeepSeek/NVIDIA key is
    configured, the DeepSeek model is built with that key instead — used for
    automatic failover on timeout / rate-limit.
    """
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

        api_key = (
            s.deepseek_api_key_2
            if use_fallback_key and s.deepseek_api_key_2
            else s.deepseek_api_key
        ) or ""

        model_params: dict[str, Any] = dict(
            model=s.get_llm_model(),
            api_key=api_key,
            base_url=s.deepseek_base_url,
            temperature=s.llm_temperature,
            request_timeout=s.deepseek_timeout,
            max_tokens=s.llm_max_tokens,
        )
        # reasoning_effort applies to gpt-oss / o-series models; "low" keeps the
        # model from spending minutes "thinking" before answering.
        if s.llm_reasoning_effort:
            model_params["reasoning_effort"] = s.llm_reasoning_effort

        kwargs["model"] = StrictOpenAICompatChatOpenAI(**model_params)
    elif s.llm_provider == "claude":
        from langchain_anthropic import ChatAnthropic

        kwargs["model"] = ChatAnthropic(
            model=s.get_llm_model(),
            api_key=s.anthropic_api_key or "",
            temperature=s.llm_temperature,
        )

    return kwargs


def build_research_agent(use_fallback_key: bool = False):
    """Build and return the compiled orchestrator deep agent.

    The orchestrator has two lightweight tools (``resolve_company`` and
    ``internet_search``), delegates heavy analysis to five specialist
    sub-agents, and is equipped with:
    - **Long-term memory** via CompositeBackend (/memories/ persists across sessions)
    - **Skills** (progressive disclosure) for Indian equity, annual-report,
      and portfolio-strategy domain knowledge
    - **Checkpointer** for conversation continuity within a session

    When ``use_fallback_key`` is True, a separate agent is built/cached using the
    second DeepSeek/NVIDIA key — used for automatic failover on timeout / rate-limit.
    """
    global _agent, _agent_fallback
    cached = _agent_fallback if use_fallback_key else _agent
    if cached is not None:
        return cached

    extra = _get_model_kwargs(use_fallback_key=use_fallback_key)

    if "model" in extra:
        model = extra.pop("model")
    else:
        model = _get_model_string()

    memory_cfg = get_memory_config()
    subagents = get_all_subagents()

    print(
        f"[ORCHESTRATOR] Building research agent "
        f"(model={model}, fallback_key={use_fallback_key})"
    )
    agent = create_deep_agent(
        model=model,
        tools=[resolve_company, internet_search],
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents=subagents,
        **memory_cfg,
    )

    if use_fallback_key:
        _agent_fallback = agent
    else:
        _agent = agent
    return agent


def build_react_agent(use_fallback_key: bool = False):
    """Build and return a single-agent LangGraph ReAct agent.

    Unlike the deep agent, this is ONE agent with a flat set of all tools and no
    sub-agent delegation, so a query resolves in a short reason→tool→reason loop
    (typically 2-4 LLM calls) instead of the deep agent's many nested sub-agent
    runs. It uses the same model/keys and the shared checkpointer for
    conversation continuity. Long-term `/memories/` filesystem and skills (deep
    agent only) are not available in this mode.
    """
    from langgraph.prebuilt import create_react_agent

    from src.agents.prompts.orchestrator import REACT_AGENT_PROMPT
    from src.agents.tools import get_all_tools

    global _react_agent, _react_agent_fallback
    cached = _react_agent_fallback if use_fallback_key else _react_agent
    if cached is not None:
        return cached

    extra = _get_model_kwargs(use_fallback_key=use_fallback_key)
    model = extra.pop("model") if "model" in extra else _get_model_string()

    memory_cfg = get_memory_config()

    print(
        f"[ORCHESTRATOR] Building ReAct agent "
        f"(model={model}, fallback_key={use_fallback_key})"
    )
    agent = create_react_agent(
        model=model,
        tools=get_all_tools(),
        prompt=REACT_AGENT_PROMPT,
        checkpointer=memory_cfg.get("checkpointer"),
        store=memory_cfg.get("store"),
    )

    if use_fallback_key:
        _react_agent_fallback = agent
    else:
        _react_agent = agent
    return agent


def _get_agent(use_fallback_key: bool = False):
    """Return the active agent for the configured ``AGENT_MODE``.

    Defaults to the fast single ReAct agent; set ``AGENT_MODE=deep`` to use the
    multi-subagent deepagents orchestrator instead.
    """
    if get_settings().agent_mode == "deep":
        return build_research_agent(use_fallback_key=use_fallback_key)
    return build_react_agent(use_fallback_key=use_fallback_key)


def stream_research_agent(payload: dict[str, Any], config: dict[str, Any]):
    """Yield synthesis tokens from the active agent as they are generated.

    Uses LangGraph ``stream_mode="messages"`` to surface token-level chunks from
    the final LLM. Failover is best-effort: if the primary key errors *before*
    any token is emitted, we retry once with the second DeepSeek/NVIDIA key;
    once streaming has started we cannot safely restart, so later errors
    propagate to the caller.
    """
    from openai import APIConnectionError, APITimeoutError, RateLimitError

    s = get_settings()

    def _stream(use_fallback: bool):
        for chunk, _meta in _get_agent(use_fallback_key=use_fallback).stream(
            payload, config=config, stream_mode="messages"
        ):
            text = getattr(chunk, "content", None)
            if text:
                yield text

    emitted = False
    try:
        for text in _stream(use_fallback=False):
            emitted = True
            yield text
    except (APITimeoutError, APIConnectionError, RateLimitError):
        key2 = s.deepseek_api_key_2
        if emitted or not (s.llm_provider == "deepseek" and key2 and key2 != s.deepseek_api_key):
            raise
        print("[ORCHESTRATOR] Primary key failed mid-stream (pre-token); retrying with DEEPSEEK_API_KEY_2")
        yield from _stream(use_fallback=True)


@traceable(name="agents.invoke_research_agent")
def invoke_research_agent(payload: dict[str, Any], config: dict[str, Any]):
    """Invoke the active agent with automatic failover to a second
    DeepSeek/NVIDIA key on timeout / rate-limit / connection errors.

    A read-timeout means the primary key authenticated fine but the model was
    slow; the second key mainly helps against rate-limit (429) or soft
    throttling, but we also retry it on timeout as a best-effort recovery.
    The same ``thread_id`` config is reused — LangGraph does not checkpoint a
    failed model step, so the fallback re-runs it cleanly.
    """
    from openai import APIConnectionError, APITimeoutError, RateLimitError

    s = get_settings()
    try:
        return _get_agent().invoke(payload, config=config)
    except (APITimeoutError, APIConnectionError, RateLimitError) as e:
        key2 = s.deepseek_api_key_2
        if s.llm_provider == "deepseek" and key2 and key2 != s.deepseek_api_key:
            print(
                f"[ORCHESTRATOR] Primary key failed ({type(e).__name__}); "
                f"retrying with DEEPSEEK_API_KEY_2"
            )
            return _get_agent(use_fallback_key=True).invoke(payload, config=config)
        raise
