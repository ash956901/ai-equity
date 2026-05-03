# Agent Coding Guidelines

Conventions for AI agents (Claude / Cursor / Copilot) and humans working on the AI Equity Research Platform. Read this before opening a PR.

For "what's actually built today," see [plans/SHIPPED.md](plans/SHIPPED.md). For end-to-end setup, see [GETTING_STARTED.md](GETTING_STARTED.md). For the active multi-phase plan, see [plans/07_round2_broker_grade_plan.md](plans/07_round2_broker_grade_plan.md).

---

## 1. What this repo is

- **Backend:** Python 3.11 / FastAPI / LangGraph (via `deepagents` wrapper) / Postgres 15 / Qdrant / Redis / Celery / AWS-ready.
- **Frontend:** React 19 / TypeScript / Vite / TanStack Query / Recharts (with `lightweight-charts` ready). **No Tailwind** — styling is hand-rolled CSS variables in [frontend/src/index.css](frontend/src/index.css).
- **Auth:** mandatory on every user-keyed route. Argon2id passwords, JWT access + refresh with rotation in Redis, blacklist on logout.
- **LLMs:** Groq / OpenAI / DeepSeek / Ollama, configurable via `LLM_PROVIDER`. **No Sarvam AI dependency.**
- **Vector store:** Qdrant. **Not Pinecone.**

If a doc still mentions Sarvam AI, Pinecone, Tailwind, or a `backend/` + `ai_engine/` directory split, it predates the current code — update it.

---

## 2. Build / lint / test

### Backend (`backend-ai/`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head           # 4 idempotent migrations
python -m uvicorn src.main:app --port 8001 --reload
PYTHONPATH=. pytest tests -q   # CI baseline
python -m py_compile $(find src -name '*.py')   # quick syntax sweep
```

Celery worker (optional, for ETL):
```bash
celery -A src.celery_app worker --loglevel=info -Q crawlers,parsers,embeddings,news,default
```

### Frontend (`frontend/`)

```bash
npm install                    # incl. @tanstack/react-query, lightweight-charts
npm run dev                    # http://localhost:5173
npm run build                  # production build
npm run lint                   # ESLint
npx tsc --noEmit               # type-check
```

### Docker (infra)

```bash
docker compose up -d           # Postgres + Redis + Qdrant
docker compose ps              # all Up?
docker compose down -v         # reset (deletes data)
```

---

## 3. Backend conventions (Python)

### Imports

- Standard library → third-party → local. Group separated by blank lines.
- `from typing import Optional` over `X | None` when the file targets Python 3.11 (mixed style accepted).
- Avoid wildcard imports.

### Type hints

- **Mandatory** on public function signatures. Return type included.
- Pydantic v2 `BaseModel` for any request/response or structured-output schema.
- Decimal-typed money / ratios where the DB column is Numeric.

### FastAPI routes

- Use `APIRouter(prefix=..., tags=[...])`. Re-export the router from `src/domains/<feature>/__init__.py` and register in [src/app/routers.py](backend-ai/src/app/routers.py).
- Inject the DB session via `db: Session = Depends(get_db)`.
- **Auth gate every user-keyed route** — see §4.

### Auth conventions (the rule)

Every route that reads / writes user-scoped data takes:

```python
from src.db.models import User
from src.domains.auth.dependencies import assert_self, get_current_user

@router.get("/{user_id}")
def get_thing(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_self(user_id, current_user)   # 403 if mismatch
    ...
```

For routes keyed by a resource id whose ownership is on a sibling table (portfolio, watchlist, alert, etc.), call the per-domain `assert_owns_*` helper after `get_current_user`. The canonical reference is [src/domains/auth/dependencies.py](backend-ai/src/domains/auth/dependencies.py).

Truly public routes (`/health`, `/ready`, `/metrics`, `/companies/...` reads, `/discovery/...` reads, `/timeline/`, `/auth/*`) skip the auth dep.

### Async / sync

- The router layer can be `def` or `async def`; pick whichever is natural for the underlying call.
- Tools in [src/agents/tools/](backend-ai/src/agents/tools/) are sync because LangGraph's tool-use loop is sync.
- Outbound HTTP uses `httpx` with explicit timeouts (`httpx.Client(timeout=15.0)` or `AsyncClient`).

### Logging

```python
import logging
logger = logging.getLogger(__name__)
```

`logger.info("request-end request_id=%s ...", request_id, ...)`. `print()` is banned.

The request middleware ([src/app/middleware.py](backend-ai/src/app/middleware.py)) attaches `request_id` to every log line inside a request scope.

### Database

- **Migrations are idempotent** — every column / index / table add is gated by an inspector check. Pattern in [alembic/versions/c1d2e3f4a501_auth_user_extensions.py](backend-ai/alembic/versions/c1d2e3f4a501_auth_user_extensions.py).
- Don't drop tables or columns without an explicit user ask.
- New tables get a SQLAlchemy model in [src/db/models.py](backend-ai/src/db/models.py) **and** an Alembic migration in the same change.

### Caching

- Reach for [src/services/cache_service.py](backend-ai/src/services/cache_service.py) — don't re-implement Redis. New TTLs go in `CacheTTL`. `get_user_profile_cached` / `invalidate_user_profile` are the canonical examples.
- Cache keys are namespaced via `_key(namespace, identifier)` — never write raw `eq:user_profile:...` strings in code.

### Observability

When you add a new agent, tool, or ETL pipeline, hook the existing counters in [src/observability.py](backend-ai/src/observability.py):

```python
from src.observability import record_tool_call, record_agent_invocation
record_tool_call("get_company_themes")
```

Don't introduce a parallel metrics library.

### LangGraph subagents

The 11 subagents live in [src/agents/subagents/](backend-ai/src/agents/subagents/). Each defines `name`, `description`, `system_prompt`, `tools`. Register new subagents in [src/agents/subagents/__init__.py](backend-ai/src/agents/subagents/__init__.py) and update the routing table in [src/agents/prompts/orchestrator.py](backend-ai/src/agents/prompts/orchestrator.py).

Every subagent's response prompt **must** end with:
- `## Sources` (cite filings, news, theme codes, edge labels)
- `## Suggested follow-ups` (exactly three questions)
- And whatever portion of the platform-wide skeleton applies (Domain → Asymmetric → Drivers → Risks → Macro → 2nd-order → Bull/Bear → Explained Simply).

The Pydantic contract is [src/schemas/structured_analysis.py](backend-ai/src/schemas/structured_analysis.py).

### LLM/tool separation rule

LangGraph tools do all math, ratios, vector search, DB reads, regex. LLMs interpret + synthesise. Never let an LLM compute a ratio.

---

## 4. Frontend conventions (TypeScript / React)

### Imports

Relative paths. **No `@/` alias** — that was an old plan; the actual code uses relative imports throughout. Group: external → internal → relative.

```typescript
import { useQuery } from "@tanstack/react-query";
import { Bot } from "lucide-react";

import { useAuth } from "../../app/state/AuthContext";
import { fetchQuote, type QuotePayload } from "../../shared/api/quotes";
```

### Components

- Functional + hooks only. Named exports, no default exports.
- Component file name matches export name, PascalCase: `BrokerStockPage.tsx` exports `BrokerStockPage`.
- Props typed inline or as a `Props` interface above the component.

### Server state

**Use TanStack Query for any non-trivial fetch.** The provider is wired in [frontend/src/app/state/QueryProvider.tsx](frontend/src/app/state/QueryProvider.tsx). Defaults: 60s `staleTime`, retry once except on 4xx, no refetch-on-focus.

Local fetches with `useEffect + useState` are tolerated only for one-shot effects that don't deserve cache (e.g. modal-triggered uploads). HomeView, BrokerStockPage candles, QuoteHeader polling are the canonical react-query examples.

### Auth wiring

Tokens live in `localStorage` under `eq.access_token` / `eq.refresh_token` (managed by [shared/api/core.ts](frontend/src/shared/api/core.ts)). Every fetch through `getJson` / `aiPost` / `aiGet` etc. attaches the bearer header automatically and silently retries once on 401 via `/auth/refresh`. **Don't read tokens directly** — use `useAuth()` for the user record.

The whole app sits inside `<RequireAuth>` ([frontend/src/main.tsx](frontend/src/main.tsx)). New top-level routes don't need their own gate.

### Styling

- Hand-rolled CSS variables in [frontend/src/index.css](frontend/src/index.css). One stylesheet, namespaced class names (`.broker-stock-page`, `.quote-header__price`, `.auth-card__footer-row`).
- Inline styles only for genuinely dynamic values (e.g. computed colour). Tailwind / styled-components are **not** in use.
- For new components, append the styles to the same `index.css` under a clear section comment.

### Charts

Recharts is in production today. `lightweight-charts` is added as a dep for the future broker-grade upgrade. Don't introduce a third charting lib.

### State management beyond server-state

Local component `useState` is preferred. `useReducer` for non-trivial state machines. Context is for cross-cutting (`AuthContext`). No Redux / Zustand / Jotai.

### Error handling

`ApiError` from [shared/api/core.ts](frontend/src/shared/api/core.ts) carries `status`. Surface error text in-place; don't crash the view. Silent retries are owned by the auth interceptor and react-query, not by individual components.

---

## 5. Project structure

### Backend (`backend-ai/src/`)

```
app/         FastAPI factory, lifespan, middleware, router registration
agents/      Orchestrator, 11 subagents, prompts, tools, etl_agents, memory, skills
domains/     API surface per feature (auth, home, quotes, broker, discovery, chat, etc.)
services/    Business services (cache, financial, news, portfolio, vector, market_data/, visualization)
integrations/  External provider adapters (FMP, FRED, Kite, Upstox, NewsAPI, NewsDataIO)
etl/         Crawlers, parsers, sentiment, alert_evaluator, filing_summary, monitoring, tasks
db/          SQLAlchemy session + 30+ models
llm/         LLM + embedding factories
schemas/     Pydantic (incl. structured_analysis.py)
observability.py
config.py
main.py
```

### Frontend (`frontend/src/`)

```
main.tsx                # AuthProvider + RequireAuth + QueryProvider wrap
App.tsx                 # Default view = "home"
app/
  components/           # AppContentRouter, SidebarShell, NotificationsPanel, ToastStack
  state/                # AuthContext, RequireAuth, QueryProvider
  hooks/                # useChatThreads, useNotifications, usePersistentState
  constants.ts, types.ts
features/
  auth/                 # SignUpView, LoginView, ForgotPasswordView, ResetPasswordView, AuthGate
  home/HomeView.tsx
  company/
    CompanyWorkspaceView.tsx                  (legacy)
    broker/                                    (broker-style stock page)
  chat/, compare/, dashboard/, discovery/,
  filings/, news/, portfolio/, profile/, settings/, timeline/
components/OmniSearch.tsx
shared/
  api/                  # core, auth, home, quotes, platform, external, user
  ui/                   # Reusable headers, badges
  types/
lib/api.ts              # legacy compat surface
index.css               # Hand-rolled CSS variables
```

---

## 6. Important rules

### API keys & secrets

- **Never commit** `AUTH_JWT_SECRET`, broker secrets, LLM keys. `.env` is gitignored.
- Frontend env vars must be `VITE_*`-prefixed.
- Backend env vars resolve via [src/config.py](backend-ai/src/config.py) (`get_settings()`), not `os.getenv()` ad-hoc.

### Database safety

- Don't write scripts that drop tables, truncate data, or alter schemas without an explicit user instruction.
- All schema changes ship as Alembic migrations, idempotent (inspector-gated). See pattern in [alembic/versions/b7c2e1d34a01_discovery_extensions.py](backend-ai/alembic/versions/b7c2e1d34a01_discovery_extensions.py).

### Discovery / RAG honesty

- Discovery subagent claims must cite at least one `evidence_quote` per asymmetric tag — verbatim from filings / news / transcripts. The two-pass theme tagger enforces this offline; the prompt enforces it at synthesis time.
- LLMs never invent numbers. If a tool returns nothing, say so and stop.

### Cost awareness

- Vision-LLM chart extraction is gated behind `ENABLE_CHART_EXTRACTION=true` because it's expensive.
- Cache aggressively (Redis TTLs in [services/cache_service.py](backend-ai/src/services/cache_service.py)).
- Expensive Discovery taggings run offline (Celery), not at query time.

### Backwards compatibility

- Existing route URLs and response shapes are stable. New fields are additive.
- The `lib/api.ts` legacy compatibility surface in the frontend is kept until each consumer is migrated to `shared/api/*`.

### Performance

- Async at the boundary; `asyncio.gather` for independent reads.
- Use Redis cache helpers, not custom dicts.
- Frontend code-split is route-based; long lists virtualise / paginate.

---

## 7. Git & PR conventions

- Branches: `feature/<short>` / `fix/<short>` / `chore/<short>` / `docs/<short>`.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Co-author tag for AI assistance: `Co-Authored-By: Claude <noreply@anthropic.com>`.
- PRs reference an issue or plan section. The CI baseline runs `PYTHONPATH=. pytest tests -q` — keep it green.
