"""Causal cross-industry insight prompt.

Use when a policy or theme has cascading effects across an industry that's
not the obvious one (e.g. "20% ethanol blending policy -> sugar mills boom",
"AI capex theme -> specialty lubricant demand").
"""

from typing import Any, Dict, List

from src.agents.prompts.insights._shared import (
    JSON_SCHEMA_HINT,
    SYSTEM_PROMPT,
    make_messages,
    to_json_block,
)


TEMPLATE = """\
You are surfacing a CAUSAL CROSS-INDUSTRY insight (a policy or theme whose
effect on a less-obvious sector matters more than the headline industry).

Use the context below to:
1. Identify the second-order beneficiary or loser sector/industry.
2. Explain the causal chain in <=2 sentences (why X happens, then why that
   helps/hurts Y).
3. Cite at least one piece of evidence per link in the chain.
4. Note counter-evidence when present (regulatory risk, substitute pressure,
   demand elasticity).

Theme / Policy context:
{context_block}

Sector-commodity links available:
{links_block}

Recent themes for candidate sectors:
{themes_block}

Recent events for candidate sectors:
{events_block}

{schema_hint}
"""


def build_messages(context: Dict[str, Any]) -> List[Any]:
    user = TEMPLATE.format(
        context_block=to_json_block(context.get("context", {})),
        links_block=to_json_block(context.get("links", [])),
        themes_block=to_json_block(context.get("themes", [])),
        events_block=to_json_block(context.get("events", [])),
        schema_hint=JSON_SCHEMA_HINT,
    )
    return make_messages(SYSTEM_PROMPT, user)
