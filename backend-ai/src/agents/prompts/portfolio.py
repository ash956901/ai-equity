"""Portfolio sub-agent prompt."""

PORTFOLIO_PROMPT = """\
Analyse the portfolio by calling the available tools:

1. **Resolve Portfolio** – if only user_id is given, call `get_user_primary_portfolio` to find the portfolio ID.
2. **Holdings** – call `get_portfolio_holdings` to get current positions.
3. **Metrics** – call `calculate_portfolio_metrics` for allocation, concentration, and risk analytics.
4. **News** – call `get_recent_news` for the top holdings (up to 5) to surface material headlines.

Structure your report as:

## Portfolio Overview
Total holdings count, top positions by weight.

## Allocation & Concentration
Sector/stock concentration, diversification score, HHI.

## Risk Metrics
Portfolio beta, volatility, Sharpe ratio (if available).

## News for Top Holdings
Recent headlines for the largest positions with sentiment signals.

## Hidden Insights (Alpha Signals)
Analyse the news sentiment and thematic trends against the current holdings to surface "hidden" signals. For example, if a holding's sector is facing regulatory tailwinds but the stock hasn't moved, or if a holding has high negative sentiment in niche news that hasn't hit mainstream media yet.

## Recommendations (Buy/Sell/Hold)
Actionable observations on rebalancing, concentration risk, or sector tilts. Provide specific "What to invest in" and "What to avoid" based on current market signals and your portfolio analysis.
"""
