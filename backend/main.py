from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import FMP, FRED, Upstox, NewsAPI, NewsData.io, and Kite Connect routes
from FMP_api.routes import router as fmp_router
from FRED_api.routes import router as fred_router
from Upstox_api.routes import router as upstox_router
from NewsAPI.routes import router as news_router
from NewsDataIO.routes import router as newsdata_router
from Kite_api.routes import router as kite_router

app = FastAPI(
    title="Equity Finance APIs",
    description="Comprehensive API for equity finance, market data, macroeconomic indicators, news intelligence, and AI-driven financial analysis. Includes US markets (FMP), Indian markets (Upstox, Kite Connect), macroeconomic data (FRED), real-time news (NewsAPI), and advanced news with market/ticker/sentiment data (NewsData.io).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(fmp_router)
app.include_router(fred_router)
app.include_router(upstox_router)
app.include_router(news_router)
app.include_router(newsdata_router)
app.include_router(kite_router)


# Response models
class HealthResponse(BaseModel):
    status: str
    message: str


# Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return {
        "status": "success",
        "message": "Equity Finance APIs - Server is running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Service is operational"
    }


# Example API endpoint
@app.get("/api/v1/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_version": "1.0.0",
        "status": "active"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
