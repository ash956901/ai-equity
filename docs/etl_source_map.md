# ETL Source Map

Source-of-truth for every ingestion pipeline behind the Insight Engine. Each
row identifies how the data flows from source -> Postgres + Qdrant -> agents.
The implementation lives under `backend-ai/src/etl/`.

Authority: this document is wired into the runtime via
`backend-ai/src/etl/source_registry.py`, which loads
`backend-ai/src/etl/sources.yaml`. Update both when you change cadence,
quotas, or kill switches.

## Conventions

- **Frequency** is the Celery beat cadence (timezone `Asia/Kolkata`).
- **Dedup key** prevents duplicate ingestion across retries.
- **Storage targets** are the Postgres table(s) and Qdrant collection(s).
- **Quota** is requests per minute through the Redis token bucket guard
  (`src.etl.guardrails.RateLimiter`).
- **Kill switch** is a config flag - set the source name to `false` in the
  `etl.disabled_sources` setting (or the `ETL_DISABLED_SOURCES` env var) to
  pause that pipeline without code changes.

## Filings

| Source | Frequency | Dedup key | Storage | Quota | TOS notes |
|--------|-----------|-----------|---------|-------|-----------|
| NSE Corporate Announcements API | 9:30/11:30/13:30/15:30/17:30 IST | `document_hash` (SHA-256 of payload) | `filings` + `filing_pages` + Qdrant `company_filings` | 30 rpm | Public; respect cookie/header conventions; back off on 4xx |
| Company IR Sites (auto-discovered) | Saturday 02:00 | `document_hash` | same as above | 12 rpm per host | Honour `robots.txt`; UA includes contact |

## News

| Source | Frequency | Dedup key | Storage | Quota | TOS notes |
|--------|-----------|-----------|---------|-------|-----------|
| NewsAPI `/v2/everything` | hourly portfolio sweep | `source_url` | `news_articles` + Qdrant `news_articles` | 30 rpm (free tier soft cap) | Free tier only allows 24h history |
| NewsData.io `/news` | hourly broad sweep | `source_url` | same | 20 rpm | Credits-based; track via `ETLRun.metadata.requests` |
| Google News RSS | hourly per ticker | `source_url` | same | 60 rpm | Public RSS; conservative UA |

## Transcripts

| Source | Frequency | Dedup key | Storage | Quota | TOS notes |
|--------|-----------|-----------|---------|-------|-----------|
| Company IR Concall pages | Sunday 03:30 | `document_hash` | `transcripts` + `transcript_segments` + Qdrant `transcripts` | 6 rpm per host | TOS varies; avoid behind-login pages |
| Optional aggregator (AlphaStreet/Researchbytes) | Sunday 03:30 | `document_hash` | same | per provider | Paid; gate with kill switch |

## Social / Alt-data

| Source | Frequency | Dedup key | Storage | Quota | TOS notes |
|--------|-----------|-----------|---------|-------|-----------|
| Reddit (`r/IndianStockMarket`, `r/IndianStreetBets`, `r/StocksAndTrading`) | hourly | `(source, source_post_id)` | `social_posts` + Qdrant `social_posts` | 60 rpm | Public; respect deletion (run reaper daily) |
| StockTwits | hourly per ticker | `(source, source_post_id)` | same | 30 rpm | Free tier covers most; rate-limit headers respected |
| X / Twitter v2 (optional) | 15 min portfolio | `(source, source_post_id)` | same | per access tier | Compliance-required deletion propagation |
| Telegram (public channels via Bot API) | hourly | `(source, source_post_id)` | same | per token | Bot must be added to public channel |

## Macro / Commodity / FX

| Source | Frequency | Dedup key | Storage | Quota | TOS notes |
|--------|-----------|-----------|---------|-------|-----------|
| FRED (US macro) | Daily 06:30 | `(code, observation_date)` | `macro_series` | 60 rpm | API key required; free |
| RBI (Indian rates / FX) | Daily 06:30 | `(code, observation_date)` | `macro_series` | 30 rpm | Public CSV; no auth |
| MCX/NCDEX (commodity proxies via FMP/yfinance) | Hourly when energy market open | `(code, observation_date)` | `commodity_series` | 30 rpm | API ToS of upstream provider |
| ICE Brent / NYMEX WTI (yfinance proxy) | Hourly | same | same | 60 rpm | Yahoo TOS - non-commercial |

## Insight Pipeline (downstream)

| Job | Frequency | Inputs | Outputs |
|-----|-----------|--------|---------|
| `etl.tag_themes` | Daily 02:00 | `filings`, `news_articles`, `transcripts`, `social_posts`, `theme_taxonomy` | `company_themes` + `relation_edges` |
| `etl.extract_events` | Daily 02:30 | same | `events`, `policies`, `relation_edges` |
| `etl.compute_daily_insights` | Daily 03:00 | `company_themes`, `events`, `policies`, `commodity_series`, `social_posts` | `insights`, `insight_evidence` |
| `etl.revalidate_insights` | Daily 04:30 | `insights`, FMP/Upstox prices, fresh news | `insight_outcomes`; archives stale insights |

## Confidence framework

`confidence = w_quality * source_quality + w_recency * recency_decay(t) + w_corroboration * log(1 + n_independent_sources)`

`source_quality` lives in the `source_quality` table. Defaults seeded by
`scripts/seed_source_quality.py`:

- Filings: 0.95
- Tier-1 news (Reuters, BS, Mint, Moneycontrol): 0.80
- Tier-2 news (Google RSS aggregations): 0.60
- Transcripts: 0.90
- Social - StockTwits/Reddit: 0.40
- Social - anonymous Telegram: 0.20
- Macro/commodity: 0.85

Weights are configurable via `etl.confidence_weights` settings.

## Kill switches & retention

- `ETL_DISABLED_SOURCES` (comma-separated) - mute any source without a
  deploy.
- `social_posts.deleted_upstream_at` - reaper job at 03:30 daily nulls
  body of posts that have been deleted on the platform (TOS compliance).
- All quota / kill / retry stats are recorded in `etl_runs.metadata`.

## Files of record

- Reference YAML: [backend-ai/src/etl/sources.yaml](../backend-ai/src/etl/sources.yaml)
- Loader: [backend-ai/src/etl/source_registry.py](../backend-ai/src/etl/source_registry.py)
- Rate limiter / kill switch: [backend-ai/src/etl/guardrails.py](../backend-ai/src/etl/guardrails.py)
- Source-quality seed: [backend-ai/scripts/seed_source_quality.py](../backend-ai/scripts/seed_source_quality.py)
- Sector <-> commodity seed: [backend-ai/src/etl/sector_commodity_links.yaml](../backend-ai/src/etl/sector_commodity_links.yaml)
