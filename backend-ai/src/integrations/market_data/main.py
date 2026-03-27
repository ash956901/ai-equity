"""Standalone entry point for external market-data APIs (optional)."""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.integrations.market_data.routes import (
    fmp_router,
    fred_router,
    kite_router,
    news_router,
    newsdata_router,
    upstox_router,
)

load_dotenv()

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
        "src.integrations.market_data.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
