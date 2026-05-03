"""Transcript Analyst sub-agent definition."""

from src.agents.prompts.transcript_analyst import TRANSCRIPT_ANALYST_PROMPT
from src.agents.tools.transcripts import (
    get_transcript_segments,
    list_recent_transcripts,
    search_transcripts,
)


def get_transcript_analyst_subagent() -> dict:
    """Return the transcript-analyst sub-agent configuration."""
    return {
        "name": "transcript-analyst",
        "description": (
            "Read earnings call transcripts; surface guidance, capex, and "
            "supply-chain commentary with verbatim quotes."
        ),
        "system_prompt": TRANSCRIPT_ANALYST_PROMPT,
        "tools": [
            list_recent_transcripts,
            search_transcripts,
            get_transcript_segments,
        ],
    }
