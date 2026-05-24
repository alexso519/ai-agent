"""API v1 route definitions.

Governance: Section 1 — FastAPI Application Architecture
"""

from fastapi import APIRouter

router = APIRouter(tags=["v1"])


@router.get("/workflows")
async def list_workflows():
    """List all workflows. Phase 1 implementation."""
    return {"workflows": []}


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow by ID. Phase 1 implementation."""
    return {"workflow_id": workflow_id, "status": "not_implemented"}