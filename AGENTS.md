# Agent Coding Guidelines

This document provides guidelines for AI agents working on the AI-Native Equity Research Platform (EquityAI).

## Project Overview

- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4 + ESLint
- **Backend**: FastAPI (Python) - Financial data APIs
- **Backend-AI**: Python - AI agents, RAG pipeline, knowledge graphs
- **AI Assistant**: "Iris" - Domain-specific chatbot powered by Sarvam AI

---

## Build/Lint/Test Commands

### Frontend (in `frontend/`)

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build

# Type checking
npx tsc --noEmit

# Linting (ESLint)
npm run lint

# Preview production build
npm run preview
```

### Backend-AI (in `backend-ai/`)

```bash
# Install dependencies (if requirements.txt exists)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the FastAPI server
python -m uvicorn src.main:app --reload
```

### Docker

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d
```

---

## Code Style Guidelines

### TypeScript/React (Frontend)

#### Imports
- Use absolute imports with `@/` alias for src directory
- Group imports: external packages → internal packages → relative imports
- Use `type` keyword for type-only imports

```typescript
// Good
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { User } from "@/types";
import { Button } from "./button";

// Avoid
import React, { useState } from "react";
```

#### Naming Conventions
- **Components**: PascalCase (`DashboardPage`, `ThreadWelcome`)
- **Functions/Hooks**: camelCase (`useLocalRuntime`, `getStockData`)
- **Constants**: SCREAMING_SNAKE_CASE for config values
- **Files**: kebab-case for utilities, PascalCase for components
- **Types/Interfaces**: PascalCase with descriptive names

#### Component Patterns
- Use functional components with explicit return types for exported components
- Prefer named exports for components
- Use `FC<Props>` or inline props types for type safety
- Keep components focused (single responsibility)

```typescript
// Good
export function ChatPage() {
  return <div>...</div>;
}

// Avoid anonymous default exports
export default () => <div>...</div>;
```

#### State Management
- Use React 19 hooks (`use` prefix patterns)
- Prefer `useState` for local state
- Extract complex logic to custom hooks

#### Styling
- Use Tailwind CSS classes (no inline styles unless dynamic)
- Use `cn()` utility for conditional classes
- Follow design system tokens (see `index.css`)

#### Error Handling
- Handle API errors gracefully with fallback UI
- Use TypeScript's type narrowing for null checks
- Provide user-friendly error messages

---

### Python (Backend/Backend-AI)

#### Imports
- Standard library imports first
- Third-party imports second
- Local imports last
- Use explicit relative imports for packages

```python
# Good
import os
from typing import Optional, List
import httpx
from pydantic import BaseModel, Field
from .client import FMPClient
```

#### Naming Conventions
- **Classes**: PascalCase (`FMPClient`, `StockQuote`)
- **Functions/Methods**: snake_case (`get_company_profile`, `async def fetch_data`)
- **Constants**: SCREAMING_SNAKE_CASE
- **Variables**: snake_case

#### Type Hints
- Use type hints for all function parameters and return values
- Use `Optional[X]` instead of `X | None`
- Use `List[X]`, `Dict[X, Y]` from typing (not built-in generics)

```python
# Good
async def get_stock_quote(symbol: str) -> List[StockQuote]:
    ...

# Avoid
async def get_stock_quote(symbol) -> list:
    ...
```

#### Pydantic Models
- Use Pydantic v2 for data validation
- Define optional fields with `Optional[X] = None`
- Use `Field` for descriptions and validation

```python
class StockQuote(BaseModel):
    symbol: str
    price: Optional[float] = None
    volume: Optional[int] = Field(None, description="Trading volume")
```

#### FastAPI Routes
- Use `APIRouter` with prefix and tags
- Define response models explicitly
- Document endpoints with docstrings
- Use `HTTPException` for error handling

```python
router = APIRouter(prefix="/fmp", tags=["FMP API"])

@router.get("/quote/{symbol}", response_model=List[StockQuote])
async def get_stock_quote(
    symbol: str = Path(..., description="Stock ticker symbol")
):
    """Get real-time stock quote with current price and metrics."""
    try:
        data = await fmp_client.get_quote(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Async Patterns
- Use `async/await` consistently
- Use `httpx.AsyncClient` for HTTP requests
- Set appropriate timeouts (default 30s)

#### Logging
- Use `logging.getLogger(__name__)` for module loggers
- Log errors with appropriate levels

```python
import logging
logger = logging.getLogger(__name__)

logger.error(f"HTTP error occurred: {e}")
```

---

## Architecture Patterns

### Frontend Structure

```
frontend/src/
├── components/       # Reusable UI components
│   ├── layout/       # Layout components (Sidebar, DashboardLayout)
│   └── assistant-ui/ # AI chat components
├── pages/            # Page components
├── providers/        # Context providers
├── lib/              # Utilities (cn, API helpers)
├── App.tsx           # Root component
└── main.tsx          # Entry point
```

### Backend-AI Structure

```
backend-ai/src/
├── app/              # FastAPI app factory, middleware, router registration
├── agents/           # Deep-agent orchestrator, prompts, subagents, tools
├── domains/          # Domain routes + service layer (chat, companies, etc.)
├── integrations/     # External provider integrations (market data)
├── external_apis/    # Legacy compatibility wrappers to integrations
├── api/              # Legacy route compatibility shims
├── db/               # Database engine/session and SQLAlchemy models
├── etl/              # Data extraction and refresh tasks
├── services/         # Shared business services
├── llm/              # LLM and embedding factory
├── config.py         # Pydantic settings
└── main.py           # Thin application entry point
```

---

## Important Notes

### API Keys
- Never commit API keys to version control
- Use environment variables (`.env` files)
- Frontend keys must be prefixed with `VITE_` for Vite
- Backend keys are accessed via `os.getenv()` or `python-dotenv`

### Data Validation
- Always validate user input at API boundaries
- Use Pydantic models for request/response validation
- Return appropriate HTTP status codes

### Error Responses
- Frontend: Show user-friendly error messages with fallback UI
- Backend: Return structured error responses with `HTTPException`

### Performance
- Use async/await for I/O-bound operations
- Implement caching where appropriate (Redis for backend, React Query for frontend)
- Lazy load routes/components in frontend

### Security
- Never expose sensitive data in error messages
- Sanitize user input before database queries
- Use parameterized queries for database operations
