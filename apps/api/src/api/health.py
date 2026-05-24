"""Health check endpoints (no auth required).

Governance: Section 13 — Observability Validation Strategy
"""

from fastapi import APIRouter

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health_check():
    """Liveness probe — returns 200 when the service is alive."""
    return {"status": "healthy", "service": "api"}


@health_router.get("/ready")
async def readiness_check():
    """Readiness probe — returns 200 when the service is ready to serve traffic."""
    return {"status": "ready", "service": "api", "version": "1.0.0"}