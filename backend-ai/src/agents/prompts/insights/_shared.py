"""Shared utilities for insight-type prompt templates."""

from __future__ import annotations

import json
from typing import Any, Dict, List


SYSTEM_PROMPT = (
    "You are an Indian-equity research analyst writing concise insight cards for a "
    "Discovery feed. INR/Cr units. Always cite at least one piece of evidence. "
    "Always include counter-evidence when contradicting signals exist. Refuse to "
    "produce insights without evidence. Respond strictly as JSON with the schema "
    "described in the user prompt."
)


JSON_SCHEMA_HINT = """
Respond strictly as JSON in this schema:

{
  "headline": "<<=120 chars, plain text, no markdown>>",
  "narrative": "<<=600 chars explaining the cause -> effect chain>>",
  "predicted_direction": "up|down|neutral",
  "horizon_days": 30,
  "primary_companies": [{"company_id": "<uuid or ticker>", "role": "beneficiary|loser"}],
  "related_themes": ["<theme_code>", "..."],
  "related_sectors": ["<sector name>", "..."],
  "evidence": [{"source_type": "filing|news|transcript|social|macro|commodity|relation|theme|event",
                "source_id": "<id>",
                "snippet": "<<=180 chars>>"}],
  "counter_evidence": [{"source_type": "...", "source_id": "...", "snippet": "..."}]
}

If you cannot identify >=1 evidence item, return {"skip": true, "reason": "no evidence"}.
"""


def to_json_block(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, default=str, indent=2)


def make_messages(system_prompt: str, user_prompt: str) -> List[Any]:
    """Return a list of LangChain message objects, importing lazily so this
    module can be unit-tested without LangChain installed."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        return [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    except ImportError:
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
