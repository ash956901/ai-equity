"""Compatibility layer for OpenAI-style providers with strict message schemas.

Some OpenAI-compatible endpoints (for example NVIDIA NIM) reject LangChain's
multi-part message content payloads and require plain string content.
This middleware normalizes message content before API calls.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI


def _normalize_content(content: Any) -> str:
    """Convert message content into a strict string payload."""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
        return json.dumps(content, ensure_ascii=True)

    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, str):
                chunks.append(part)
                continue

            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                    continue
                if part.get("type") == "image_url":
                    chunks.append("[image]")
                    continue
                chunks.append(json.dumps(part, ensure_ascii=True))
                continue

            chunks.append(str(part))

        return "\n".join(chunk for chunk in chunks if chunk).strip()

    return str(content)


class StrictOpenAICompatChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass that sanitizes message payloads."""

    def _sanitize_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        sanitized: list[BaseMessage] = []
        for msg in messages:
            normalized = _normalize_content(msg.content)
            if isinstance(msg, ToolMessage) and not normalized:
                normalized = "(no output)"
            sanitized.append(msg.model_copy(update={"content": normalized}))
        return sanitized

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        return super()._generate(
            self._sanitize_messages(messages),
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

    async def _agenerate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        return await super()._agenerate(
            self._sanitize_messages(messages),
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

    def _stream(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        return super()._stream(
            self._sanitize_messages(messages),
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

    async def _astream(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        async for chunk in super()._astream(
            self._sanitize_messages(messages),
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        ):
            yield chunk
