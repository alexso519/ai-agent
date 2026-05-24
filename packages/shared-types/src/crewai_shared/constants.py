"""Shared constants for the CrewAI Enterprise Control Center.

Governance: Section 9 — Execution State Machine
"""

from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow execution status enum.

    Represents the current state of a workflow execution.
    State transitions are validated by WorkflowStateMachine.
    """

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUSPENDED = "SUSPENDED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUCCESS = "SUCCESS"


class AgentExecutionStatus(str, Enum):
    """Per-agent execution status within a workflow."""

    IDLE = "IDLE"
    THINKING = "THINKING"
    ACTING = "ACTING"
    TOOL_CALLING = "TOOL_CALLING"
    OBSERVING = "OBSERVING"
    AWAITING_HITL = "AWAITING_HITL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExecutionQueue(str, Enum):
    """Celery queue names for task routing."""

    HIGH = "workflow_high"
    DEFAULT = "workflow_default"
    LOW = "workflow_low"
    CONTROL = "workflow_control"
    HITL = "hitl"


# ─── System Limits ───────────────────────────────────────────────────────

MAX_TERMINAL_ENTRIES = 10_000
SSE_KEEPALIVE_INTERVAL_S = 30
SSE_MAX_RETRIES = 5
SSE_BACKOFF_S = [1, 2, 4, 8, 16]
SYNC_DEBOUNCE_MS = 300

CELERY_SOFT_TIME_LIMIT = 3600
CELERY_HARD_TIME_LIMIT = 3900
CELERY_RESULT_EXPIRY_S = 86400

TOKEN_LIMITS = {
    "AGENT_THOUGHT_OUTPUT": 1000,
    "TOOL_RESULT_OUTPUT": 1000,
    "AGENT_COMPLETED_OUTPUT": 2000,
    "TERMINAL_ENTRY_MESSAGE": 5000,
}