---
name: portfolio-strategy
description: Use this skill when analysing user portfolios, suggesting allocation changes, or evaluating portfolio-level risk. Covers diversification, concentration risk, sector allocation, and rebalancing strategies for Indian equity portfolios.
---

# Portfolio Strategy

## Overview

This skill provides frameworks for portfolio-level analysis and strategy recommendations tailored to the Indian equity market.

## Portfolio Health Checks

### Concentration Risk
- **Single stock**: No single holding should exceed 15-20% of portfolio value.
- **Top 5 holdings**: Should ideally be <50% of total portfolio.
- **Sector**: No single sector should exceed 25-30% allocation.
- **Market cap**: Balanced allocation across large, mid, and small caps based on risk appetite.

### Diversification Assessment
| Risk Profile | Large Cap | Mid Cap | Small Cap |
|-------------|-----------|---------|-----------|
| Conservative | 70-80% | 15-20% | 0-10% |
| Moderate | 50-60% | 25-30% | 10-20% |
| Aggressive | 30-40% | 30-35% | 25-35% |

### Sector Allocation (Nifty 50 benchmark weights for reference)
- Financial Services: ~33%
- IT: ~13%
- Oil & Gas: ~12%
- FMCG: ~9%
- Auto: ~7%
- Pharma: ~4%
- Metals: ~3%
- Others: ~19%

Significant deviation from benchmark weights should be intentional and justified.

## Rebalancing Triggers

Recommend rebalancing when:
1. Any single stock drifts >5% from target allocation.
2. Any sector drifts >10% from target allocation.
3. Market cap category drifts >15% from target allocation.
4. After significant corporate events (mergers, demergers, rights issues).
5. At least once per quarter regardless of drift.

## Risk Metrics to Report

- **Portfolio Beta**: Weighted average beta vs Nifty 50.
- **Dividend Yield**: Weighted average portfolio dividend yield.
- **PE Ratio**: Weighted average PE of the portfolio.
- **Sector Herfindahl Index**: Measure of sector concentration (lower = more diversified).
- **Correlation**: Identify highly correlated holdings that don't add diversification.

## Actionable Recommendations Format

When suggesting portfolio changes, structure as:
1. **Current State**: Summarise current allocation, concentration, and risk metrics.
2. **Issues Identified**: List specific problems (over-concentration, missing sectors, etc.).
3. **Recommended Actions**: Specific buy/sell/hold with rationale.
4. **Target State**: What the portfolio should look like after rebalancing.
5. **Monitoring Points**: What to track going forward.

## Indian-specific Considerations

- Tax implications: LTCG (>1 year, >₹1.25L) at 12.5%, STCG at 20%.
- Dividend taxation: Taxable in hands of investor at slab rate.
- STT already paid on exchange transactions.
- Consider lock-in periods for ELSS mutual funds if part of portfolio.
- Factor in upcoming IPOs or NFOs the user might want to participate in.
