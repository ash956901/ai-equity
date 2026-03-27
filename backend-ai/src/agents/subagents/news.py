"""News sentiment sub-agent definition."""

from src.agents.prompts.news import NEWS_SENTIMENT_PROMPT
from src.agents.tools.news import get_recent_news
from src.agents.tools.web_search import internet_search


def get_news_subagent() -> dict:
    """Return the news-sentiment sub-agent configuration."""
    return {
        "name": "news-sentiment",
        "description": (
            "Aggregate recent news and assess sentiment for one or more companies. "
            "Pass the company_id UUID(s) in your task prompt."
        ),
        "system_prompt": NEWS_SENTIMENT_PROMPT,
        "tools": [
            get_recent_news,
            internet_search,
        ],
    }
