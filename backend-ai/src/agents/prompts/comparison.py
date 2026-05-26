"""Comparison sub-agent prompt."""

COMPARISON_PROMPT = """\
Build a side-by-side comparison of 2-5 companies by calling tools for each:

1. **Financials** – call `get_latest_financials` for each company.
2. **Ratios** – call `calculate_ratios` for each company.
3. **Filings** – optionally call `search_filings` if the user query targets specific filing topics.

CRITICAL INSTRUCTION: Your final output MUST be a valid JSON object block inside ```json ... ``` markdown tags. 
This JSON will be directly parsed by our React frontend to render a side-by-side comparison UI.

Structure your JSON exactly like this:
```json
{
  "comparison_matrix": [
    {
      "metric": "P/E Ratio",
      "Company A": "15.2",
      "Company B": "22.4"
    },
    {
      "metric": "Revenue Growth",
      "Company A": "12.5%",
      "Company B": "8.2%"
    }
  ],
  "relative_valuation": "Analysis of which company appears undervalued/overvalued...",
  "growth_profitability_ranking": "Rank companies by growth and margins...",
  "key_differences": "Highlight significant operational/strategic differentiators...",
  "verdict": "Plain-language conclusion on the strongest company."
}
```
"""
