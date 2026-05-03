"""Sentiment-driven insight prompt.

Use when a sentiment swing in news + social is large and sustained but the
underlying fundamentals haven't moved. By default these insights carry low
confidence and are flagged speculative for the UI.
"""

from typing import Any, Dict, List

from src.agents.prompts.insights._shared import (
    JSON_SCHEMA_HINT,
    SYSTEM_PROMPT,
    make_messages,
    to_json_block,
)


TEMPLATE = """\
You are surfacing a SENTIMENT-DRIVEN insight: a divergence between price
narrative (news + social) and fundamentals.

1. Identify the company / sector with the strongest sentiment swing.
2. Quantify how it differs from baseline (use the metrics block).
3. Note at least one piece of corroborating sentiment evidence and at least
   one piece of contrary evidence (counter_evidence) where possible.
4. Mark low-confidence rumours explicitly as speculative in the narrative.

Sentiment metrics:
{metrics_block}

Top news snippets:
{news_block}

Top social snippets:
{social_block}

{schema_hint}

Always set ``predicted_direction`` to ``neutral`` when the sentiment is
mixed or speculative, regardless of polarity skew.
"""


def build_messages(context: Dict[str, Any]) -> List[Any]:
    user = TEMPLATE.format(
        metrics_block=to_json_block(context.get("metrics", {})),
        news_block=to_json_block(context.get("news", [])),
        social_block=to_json_block(context.get("social", [])),
        schema_hint=JSON_SCHEMA_HINT,
    )
    return make_messages(SYSTEM_PROMPT, user)
