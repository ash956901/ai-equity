"""Supply-chain ripple insight prompt.

Use when an event at company A propagates downstream/upstream to companies
linked via supplies/customer_of/competes_with edges.
"""

from typing import Any, Dict, List

from src.agents.prompts.insights._shared import (
    JSON_SCHEMA_HINT,
    SYSTEM_PROMPT,
    make_messages,
    to_json_block,
)


TEMPLATE = """\
You are surfacing a SUPPLY-CHAIN RIPPLE insight: an event at one company
that meaningfully affects suppliers, customers, or close competitors.

For the source event below:

1. Map the affected entities via the supply-chain relations provided.
2. Pick the single most likely beneficiary OR loser to highlight (one card
   per ripple direction; do NOT mix).
3. Explain in <=2 sentences how the impact propagates and over what horizon.
4. Cite the source event, the relation, and any corroborating news /
   transcript snippet.

Source event:
{event_block}

Supply-chain edges relevant to the source company:
{edges_block}

Recent transcript / news snippets for ripple candidates:
{snippets_block}

{schema_hint}
"""


def build_messages(context: Dict[str, Any]) -> List[Any]:
    user = TEMPLATE.format(
        event_block=to_json_block(context.get("event", {})),
        edges_block=to_json_block(context.get("edges", [])),
        snippets_block=to_json_block(context.get("snippets", [])),
        schema_hint=JSON_SCHEMA_HINT,
    )
    return make_messages(SYSTEM_PROMPT, user)
