"""Authentication domain (signup, login, JWT, password reset)."""

from src.domains.auth.routes import router as auth_router

__all__ = ["auth_router"]
