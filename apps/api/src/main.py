"""CrewAI Enterprise Control Center — API Server Entry Point

Governance: Section 1 — FastAPI Application Architecture
Application factory pattern with lifespan-managed startup/shutdown.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.health import health_router
from .api.routes import router as api_router
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Deterministic lifecycle for all backend services.

    Startup (ordered by dependency):
    1. Database connection pool
    2. Redis connections
    3. Event engine
    4. Service registry

    Shutdown (reverse order).
    """
    # === STARTUP ===
    # Phase 1 implementation: initialize db, redis, events, services
    yield
    # === SHUTDOWN ===
    # Phase 1 implementation: cleanup in reverse order


def create_app() -> FastAPI:
    """Application factory — no global state. No hidden singletons."""
    app = FastAPI(
        title="CrewAI Control Center API",
        version=settings.API_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Health endpoints (no auth)
    app.include_router(health_router)

    # API routes
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()