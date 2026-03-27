"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.app.lifespan import app_lifespan
from src.app.middleware import register_middleware
from src.app.routers import register_routers


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Equity Research Platform",
        description="Backend-only AI-native equity research system for Indian equities.",
        version="0.2.0",
        lifespan=app_lifespan,
    )

    register_middleware(app)
    register_routers(app)

    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.get("/")
    def root():
        """Root status endpoint."""
        return {"status": "ok", "service": "ai-equity-research", "version": "0.2.0"}

    @app.get("/health")
    def health():
        """Health endpoint for load balancers."""
        return {"status": "healthy"}

    @app.get("/api/v1/status")
    def api_status():
        """Legacy API status endpoint."""
        return {"api_version": "1.0.0", "status": "active"}

    return app
