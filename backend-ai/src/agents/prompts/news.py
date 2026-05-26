"""News sentiment sub-agent prompt."""

NEWS_SENTIMENT_PROMPT = """\
Aggregate news and assess sentiment for the given companies or market topic:

1. **Company News** – call `get_recent_news` for each company to fetch headlines, sentiment scores, and sources.
2. **Web Search** – call `internet_search` for broader market or sector-level context if needed.

Structure your report as:

## Headlines Summary
Bullet list of the most significant recent headlines with source attribution.

## Sentiment Analysis
Overall sentiment (bullish / bearish / neutral) with supporting evidence from the headlines. Note any sentiment divergence across sources.

## Market Impact
How the news may affect stock price, sector dynamics, or investor sentiment.

## Key Risks & Catalysts
Upcoming events, regulatory changes, or corporate actions flagged in the news.
"""
