"""Groq API compatibility layer.

Groq's API is stricter than OpenAI/Anthropic about message formats:
- Tool messages MUST have non-null string content
- Empty or None content causes 400 errors
- Llama models often fail to generate proper tool_calls JSON format

This module provides a ChatOpenAI subclass that sanitizes messages
and retries with lower temperature on tool call failures.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, ToolMessage

logger = logging.getLogger(__name__)

# Retry config constants
GROQ_MAX_RETRIES = 2
GROQ_INITIAL_TEMP = 0.3


class GroqChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass that sanitizes messages and handles tool call failures."""

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        sanitized = self._sanitize_messages(messages)
        
        # Try with retries on tool call failure
        last_error = None
        current_temp = kwargs.get('temperature', GROQ_INITIAL_TEMP)
        
        for attempt in range(GROQ_MAX_RETRIES + 1):
            try:
                adjusted_kwargs = {**kwargs, 'temperature': current_temp}
                return super()._generate(sanitized, stop=stop, run_manager=run_manager, **adjusted_kwargs)
            except Exception as e:
                error_str = str(e).lower()
                last_error = e
                
                # Check if it's a tool call failure
                if 'tool_use_failed' in error_str or 'failed_generation' in error_str or 'bad request' in error_str:
                    logger.warning(f"Tool call failed (attempt {attempt + 1}/{GROQ_MAX_RETRIES + 1}), lowering temperature from {current_temp}")
                    # Reduce temperature for next attempt
                    current_temp = max(current_temp - 0.1, 0.1)
                    continue
                else:
                    # Non-tool error, raise immediately
                    raise
        
        raise last_error

    def _sanitize_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Sanitize messages for Groq compatibility."""
        sanitized = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and not msg.content:
                msg = msg.model_copy(update={"content": "(no output)"})
            sanitized.append(msg)
        return sanitized