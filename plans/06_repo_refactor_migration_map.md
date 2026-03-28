# Repository Refactor Migration Map (No-Behavior-Change)

This document defines the staged refactor plan for the current codebase.

Goals:
- improve structure and ownership boundaries
- keep API routes and payloads stable
- avoid feature-level behavior changes
- reduce merge risk by doing incremental moves

## Principles

- **Compatibility first:** keep old import paths working during migration.
- **One boundary at a time:** app wiring -> backend domains -> frontend features.
- **No API contract drift:** URLs and response shapes remain unchanged.
- **Small PR slices:** each step should be independently deployable.

## Phase 0 - Baseline + Guardrails

- Freeze baseline endpoint checks:
  - `GET /health`
  - `GET /companies/`
  - `POST /chat/query`
  - `POST /compare/`
- Freeze frontend build + key workspace smoke flow.

## Phase 1 - App Wiring Refactor (Backend)

### Current

- `backend-ai/src/main.py`

### Target

- `backend-ai/src/app/factory.py` (FastAPI creation)
- `backend-ai/src/app/lifespan.py` (startup/bootstrap lifecycle)
- `backend-ai/src/app/middleware.py` (CORS and shared middleware)
- `backend-ai/src/app/routers.py` (router registration)
- `backend-ai/src/main.py` (thin entrypoint only)

## Phase 2 - Domain Router Facades (Backend)

### Current

- `backend-ai/src/api/routes_chat.py`
- `backend-ai/src/api/routes_upload.py`
- `backend-ai/src/api/routes_company.py`
- `backend-ai/src/api/routes_compare.py`
- `backend-ai/src/api/routes_portfolio.py`
- `backend-ai/src/api/routes_alerts.py`
- `backend-ai/src/api/routes_watchlists.py`
- `backend-ai/src/api/routes_timeline.py`
- `backend-ai/src/api/routes_screens.py`
- `backend-ai/src/api/routes_user.py`

### Target (facade layer first)

- `backend-ai/src/domains/chat/` -> exports existing chat + upload routers
- `backend-ai/src/domains/companies/` -> exports existing company router
- `backend-ai/src/domains/compare/` -> exports existing compare router
- `backend-ai/src/domains/portfolio/` -> exports existing portfolio router
- `backend-ai/src/domains/alerts/` -> exports existing alerts router
- `backend-ai/src/domains/watchlists/` -> exports existing watchlists router
- `backend-ai/src/domains/timeline/` -> exports existing timeline router
- `backend-ai/src/domains/screens/` -> exports existing screens router
- `backend-ai/src/domains/users/` -> exports existing user router

> Initial step is re-export facades only. Route logic remains in `src/api/` until later.

## Phase 3 - Service Decomposition (Backend)

### Current

- `backend-ai/src/services/realtime_data.py` (quote + financials + ratios + enrichment + provider fallback + search)

### Target

- `backend-ai/src/services/quotes_service.py`
- `backend-ai/src/services/fundamentals_service.py`
- `backend-ai/src/services/ratios_service.py`
- `backend-ai/src/services/company_enrichment_service.py`
- `backend-ai/src/services/company_search_service.py`
- `backend-ai/src/services/provider_fallbacks/` (FMP/Upstox/Kite/web adapters)
- `backend-ai/src/services/realtime_data.py` kept as compatibility orchestrator wrapper

## Phase 4 - Integrations Namespace (Backend)

### Current

- `backend-ai/src/external_apis/*`

### Target

- `backend-ai/src/integrations/market_data/*` (gradual move)
- `backend-ai/src/external_apis` retained temporarily as compatibility imports

### Phase 4 status (implemented)

- app router wiring now imports external provider routers from integration namespace:
  - `src/app/routers.py` -> `from src.integrations.market_data import ALL_EXTERNAL_ROUTERS`
- added integration-layer router/module facades:
  - `src/integrations/market_data/routes.py`
  - `src/integrations/market_data/{fmp,fred,news_api,newsdata_io,upstox,kite}.py`
  - `src/integrations/market_data/main.py`
- quote provider imports now go through integration namespace:
  - `src/services/market_data/quotes_service.py`
- `src/external_apis` remains active as compatibility package and standalone legacy entrypoint.

### Phase 4.1 status (P1 progress)

- integration-layer router exports now import provider routers through
  `src/integrations/market_data/{fmp,fred,news_api,newsdata_io,upstox,kite}.py`
  instead of directly importing from `src.external_apis.*` in `routes.py`
- provider implementations were moved under
  `src/integrations/market_data/providers/*` and now define ownership there
- legacy `src/external_apis/*` modules were converted into thin compatibility
  wrappers that re-export from integration provider modules
- chat upload flow moved from route-heavy handler to service layer:
  - added `src/domains/chat/upload_service.py`
  - `src/domains/chat/upload_routes.py` now uses DI session via `Depends(get_db)`
    and delegates processing to service methods
- added upload-service unit tests for core behaviors:
  - `tests/domains/chat/test_upload_service.py`

## Phase 5 - Frontend Split by Feature

### Current

- `frontend/src/App.tsx` (monolith)
- `frontend/src/lib/api.ts` (all endpoints and types)

### Target

- `frontend/src/app/AppShell.tsx`
- `frontend/src/app/state/`
- `frontend/src/features/chat/`
- `frontend/src/features/company/`
- `frontend/src/features/compare/`
- `frontend/src/features/portfolio/`
- `frontend/src/features/timeline/`
- `frontend/src/features/filings/`
- `frontend/src/features/news/`
- `frontend/src/features/profile/`
- `frontend/src/features/settings/`
- `frontend/src/shared/api/` (`chat.ts`, `companies.ts`, `portfolio.ts`, etc.)
- `frontend/src/shared/types/`

> Start by extracting presentational view blocks, then hooks/state, then APIs.

## Phase 6 - Docs, Schema, and Developer UX

- Align `README.md`, `GETTING_STARTED.md`, and architecture docs with actual code.
- Fix Alembic baseline so migration history matches model reality.
- Remove stale/dead references (`deep_research` and non-existent files).

## Phase 7 - Hygiene and CI

- Standardize ignores for generated files (`__pycache__`, logs, local outputs).
- Add lint/type/build checks for both backend and frontend.
- Add contract checks for key API payloads used by frontend.

## Migration Table (Old -> New)

- `src/main.py` -> `src/app/factory.py` + thin `src/main.py`
- `src/api/routes_*.py` -> `src/domains/*/` (facade first, then real move)
- `src/external_apis/*` -> `src/integrations/market_data/*` (with compatibility layer)
- `src/services/realtime_data.py` -> focused services + wrapper
- `frontend/src/App.tsx` -> `frontend/src/app/*` + `frontend/src/features/*`
- `frontend/src/lib/api.ts` -> `frontend/src/shared/api/*.ts`

## Exit Criteria

- Existing endpoints respond with same URL/shape.
- Frontend behavior unchanged (aside from bug fixes explicitly accepted).
- Monolith files reduced substantially in size.
- Docs and code structure are aligned.
