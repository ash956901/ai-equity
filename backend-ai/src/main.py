"""FastAPI main application."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.db.database import init_db
from src.api.routes_chat import router as chat_router
from src.api.routes_company import router as company_router
from src.api.routes_portfolio import router as portfolio_router
from src.api.routes_compare import router as compare_router
from src.api.routes_alerts import router as alerts_router
from src.api.routes_watchlists import router as watchlists_router
from src.api.routes_timeline import router as timeline_router
from src.api.routes_upload import router as upload_router
from src.api.routes_screens import router as screens_router
from src.api.routes_user import router as user_router
from src.external_apis import ALL_EXTERNAL_ROUTERS

logger = logging.getLogger(__name__)
settings = get_settings()


def _bootstrap_universe():
    """Background-thread helper: sync stock universe if DB is empty."""
    from sqlalchemy import func
    from src.db.database import SessionLocal
    from src.db.models import Company

    db = SessionLocal()
    try:
        count = db.query(func.count(Company.id)).scalar() or 0
        if count < 100:
            logger.info(
                "Database has only %d companies — triggering universe sync …", count
            )
            from src.services.stock_universe import StockUniverseService

            svc = StockUniverseService(db)
            stats = svc.sync_full_universe()
            logger.info("Startup universe sync complete: %s", stats)
        else:
            logger.info("Database already has %d companies, skipping startup sync.", count)
    except Exception as e:
        logger.warning("Startup universe sync failed (non-fatal): %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifespan."""
    init_db()

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _bootstrap_universe)

    yield


app = FastAPI(
    title="AI Equity Research Platform",
    description="Backend-only AI-native equity research system for Indian equities.",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(company_router)
app.include_router(portfolio_router)
app.include_router(compare_router)
app.include_router(alerts_router)
app.include_router(watchlists_router)
app.include_router(timeline_router)
app.include_router(upload_router)
app.include_router(screens_router)
app.include_router(user_router)

for _ext_router in ALL_EXTERNAL_ROUTERS:
    app.include_router(_ext_router)

_uploads_dir = Path("uploads")
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "ai-equity-research", "version": "0.2.0"}


@app.get("/health")
def health():
    """Health check for load balancers."""
    return {"status": "healthy"}


@app.get("/api/v1/status")
def api_status():
    """API status endpoint (legacy compat)."""
    return {"api_version": "1.0.0", "status": "active"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )
