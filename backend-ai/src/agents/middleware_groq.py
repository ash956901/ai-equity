"""Groq API compatibility layer.

Groq's API is stricter than OpenAI/Anthropic about message formats:
- Tool messages MUST have non-null string content
- Empty or None content causes 400 errors

This module provides a ChatOpenAI subclass that sanitizes messages
at the API call level, ensuring compatibility with all agent/sub-agent
invocations.
"""

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, ToolMessage


class GroqChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass that sanitizes messages for Groq compatibility."""

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        sanitized = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and not msg.content:
                msg = msg.model_copy(update={"content": "(no output)"})
            sanitized.append(msg)
        return super()._generate(sanitized, stop=stop, run_manager=run_manager, **kwargs)
