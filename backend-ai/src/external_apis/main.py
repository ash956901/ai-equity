"""Standalone entry point for external data APIs (optional).

In the unified setup, these routers are mounted by backend-ai/src/main.py.
This file can still be used to run the external APIs as a separate service
if desired:  python -m src.external_apis.main
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from .FMP_api.routes import router as fmp_router
from .FRED_api.routes import router as fred_router
from .Upstox_api.routes import router as upstox_router
from .NewsAPI.routes import router as news_router
from .NewsDataIO.routes import router as newsdata_router
from .Kite_api.routes import router as kite_router

app = FastAPI(
    title="Equity Finance APIs",
    description="External financial data APIs (FMP, FRED, NewsAPI, NewsDataIO, Upstox, Kite Connect).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fmp_router)
app.include_router(fred_router)
app.include_router(upstox_router)
app.include_router(news_router)
app.include_router(newsdata_router)
app.include_router(kite_router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "external-data-apis", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Service is operational"}


if __name__ == "__main__":
    uvicorn.run(
        "src.external_apis.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
