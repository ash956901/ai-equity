# Frontend API Validation Report

Date: 2026-03-28
Environment: local backend at http://localhost:8001
Scope: APIs called from frontend modules under frontend/src/shared/api/

## Summary

- Total frontend API helpers checked: 38
- Working (HTTP 2xx): 31
- Broken (HTTP 404): 3
- Input/flow-dependent (4xx but endpoint exists): 4

Main blocker:
- News/Upstox external endpoints still referenced in frontend are not present in backend:
  - /newsdata/market/headlines
  - /newsdata/sentiment/{symbol}
  - /upstox/portfolio/holdings

## Detailed Results

### core.ts

- fetchBackendHealth -> GET /health -> 200
  - sample: {"status":"healthy"}
- fetchApiStatus -> GET /api/v1/status -> 200
  - sample: {"api_version":"1.0.0","status":"active"}

### external.ts

- fetchMarketHeadlines -> GET /newsdata/market/headlines?country=in&timeframe=6&size=6 -> 404
  - sample: {"detail":"Not Found"}
- fetchHoldingsCount -> GET /upstox/portfolio/holdings -> 404
  - sample: {"detail":"Not Found"}
- fetchTickerSentiment -> GET /newsdata/sentiment/AAPL?hours_back=24&size=8&language=en -> 404
  - sample: {"detail":"Not Found"}
- fetchSecFilings (step 1) -> GET /companies/search?q=AAPL&limit=10 -> 200
  - sample: []
- fetchSecFilings (step 2) -> GET /timeline/?company_id=<valid_company_id>&limit=30 -> 200
  - sample: []
- searchCompanies -> GET /companies/search?q=RELIANCE&limit=6 -> 200
  - sample includes Reliance Industries Limited

### platform.ts

- fetchAIHealth -> GET /health -> 200
- sendChatQuery -> POST /chat/query -> 200
  - sample: assistant greeting response
- listChatSessions -> GET /chat/sessions/<user_id> -> 200
  - sample: [{"id":...,"title":"hi",...}]
- fetchCompanies -> GET /companies/?limit=5&offset=0 -> 200
- fetchCompanyDetail -> GET /companies/<valid_company_id> -> 200
- fetchCompanyFinancials -> GET /companies/<valid_company_id>/financials?periods=4 -> 200
- fetchCompanyRatios -> GET /companies/<valid_company_id>/ratios -> 200
- fetchCompanyQuote -> GET /companies/<valid_company_id>/quote -> 200
  - sample: source AlphaVantage, price + volume present
- enrichCompany -> POST /companies/<valid_company_id>/enrich -> 200
- searchCompaniesDB -> GET /companies/search?q=TCS&limit=20 -> 200
- fetchPortfolios -> GET /portfolios/?user_id=<user_id> -> 200
- createPortfolio -> POST /portfolios/ -> 201
- fetchPortfolioDetail -> GET /portfolios/<created_portfolio_id> -> 200
- addHolding -> POST /portfolios/<created_portfolio_id>/holdings -> 201
- compareCompanies -> POST /compare/ with empty company_ids -> 422
  - endpoint exists; payload invalid for business rules (needs at least 2 IDs)
- fetchAlerts -> GET /alerts/?user_id=<user_id> -> 200
- createAlertRule -> POST /alerts/ -> 201
- deleteAlert -> DELETE /alerts/<created_alert_id> -> 204
- fetchWatchlists -> GET /watchlists/?user_id=<user_id> -> 200
- createWatchlist -> POST /watchlists/ -> 201
- addToWatchlist -> POST /watchlists/<created_watchlist_id>/companies -> 201
- removeFromWatchlist -> DELETE /watchlists/<created_watchlist_id>/companies/<company_id> -> 204
- fetchTimeline -> GET /timeline/?limit=20 -> 200
- uploadDocument -> POST /chat/upload (multipart) -> 200
  - sample: {"upload_id":...,"filename":"probe.txt","status":"uploaded"}

### user.ts

- fetchUserProfile -> GET /users/<user_id> -> 200
- updateUserProfile -> PUT /users/<user_id> -> 200
- uploadProfilePic -> POST /users/<user_id>/profile-pic
  - 400 when non-image file used (expected validation)
  - 200 when valid PNG used
- submitKyc -> POST /users/<user_id>/kyc/submit -> 200
- fetchKycStatus -> GET /users/<user_id>/kyc/status -> 200
- verifyKyc -> POST /users/<user_id>/kyc/verify -> 200

## Endpoints Not Working (Action Required)

1. GET /newsdata/market/headlines -> 404
2. GET /newsdata/sentiment/{symbol} -> 404
3. GET /upstox/portfolio/holdings -> 404

These are frontend/backend contract mismatches.

## Recommendation

- Short term: switch frontend helpers in external.ts to active domain routes (companies/timeline/news domain) or hide those widgets behind feature flags.
- Medium term: define a single API contract document and CI route check that validates every frontend helper path against backend OpenAPI.
