"""Event-catalyst insight prompt.

Use when a scheduled event (investor meet, regulatory hearing, results day,
budget) is near and the directionality is asymmetric or binary.
"""

from typing import Any, Dict, List

from src.agents.prompts.insights._shared import (
    JSON_SCHEMA_HINT,
    SYSTEM_PROMPT,
    make_messages,
    to_json_block,
)


TEMPLATE = """\
You are surfacing an EVENT-CATALYST insight: a scheduled event with a clear
asymmetric or binary impact.

1. Identify the event, the date, and the company / sector affected.
2. Explain the binary / asymmetric outcome in <=2 sentences.
3. Cite the source filing / news / transcript that announced the event.
4. Add counter-evidence if there's a credible reason the catalyst could
   misfire.
5. ``horizon_days`` should typically be the number of days to the event
   plus a tactical 5-10 day window.

Source event:
{event_block}

Company / sector context:
{context_block}

Pre-event positioning evidence:
{positioning_block}

{schema_hint}
"""


def build_messages(context: Dict[str, Any]) -> List[Any]:
    user = TEMPLATE.format(
        event_block=to_json_block(context.get("event", {})),
        context_block=to_json_block(context.get("context", {})),
        positioning_block=to_json_block(context.get("positioning", [])),
        schema_hint=JSON_SCHEMA_HINT,
    )
    return make_messages(SYSTEM_PROMPT, user)
