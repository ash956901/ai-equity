"""Document insight sub-agent definition."""

from src.agents.prompts.doc_analysis import DOC_ANALYSIS_PROMPT
from src.agents.tools.vector_search import search_user_upload
from src.agents.tools.document import parse_pdf, parse_ppt, fetch_url


def get_doc_insight_subagent() -> dict:
    """Return the doc-insight sub-agent configuration."""
    return {
        "name": "doc-insight",
        "description": (
            "Analyse an uploaded document (PDF, PPT, annual report) with "
            "page-level citations. Pass user_id, upload_id, and the query "
            "in your task prompt."
        ),
        "system_prompt": DOC_ANALYSIS_PROMPT,
        "tools": [
            search_user_upload,
            parse_pdf,
            parse_ppt,
            fetch_url,
        ],
    }
