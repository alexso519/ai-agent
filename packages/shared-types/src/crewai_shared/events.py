"""Event type definitions and envelope schema.

Governance: Section 6 — Event Schema Governance
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Canonical event type registry.

    All event types must be registered here. No ad-hoc event types.
    New event types require ADR approval.
    """

    # Workflow lifecycle
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_CHECKPOINT = "WORKFLOW_CHECKPOINT"
    WORKFLOW_PAUSED = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED = "WORKFLOW_RESUMED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"

    # Agent execution
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_THOUGHT = "AGENT_THOUGHT"
    AGENT_ACTION = "AGENT_ACTION"
    AGENT_OBSERVATION = "AGENT_OBSERVATION"
    TOOL_CALLING = "TOOL_CALLING"
    TOOL_RESULT = "TOOL_RESULT"
    TOOL_ERROR = "TOOL_ERROR"
    AGENT_COMPLETED = "AGENT_COMPLETED"

    # HITL
    HITL_REQUIRED = "HITL_REQUIRED"
    HITL_APPROVED = "HITL_APPROVED"
    HITL_REJECTED = "HITL_REJECTED"
    HITL_REGENERATED = "HITL_REGENERATED"

    # Progress and metrics
    TASK_PROGRESS = "TASK_PROGRESS"
    METRICS_UPDATE = "METRICS_UPDATE"
    ERROR_OCCURRED = "ERROR_OCCURRED"


class EventSource(str, Enum):
    """Source component that emitted the event."""

    RUNTIME = "runtime"
    WORKER = "worker"
    API = "api"
    SYSTEM = "system"


class RuntimeEvent(BaseModel):
    """Universal event envelope for all system events.

    All events must:
    - Have a unique ID
    - Include correlation_id for tracing across service boundaries
    - Include the source component
    - Be schema-versioned for forward compatibility
    """

    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    execution_id: str
    correlation_id: str
    source: EventSource
    step: int = 0
    sequence: int = 0
    data: dict = Field(default_factory=dict)
    version: int = 1

    model_config = {"frozen": True}  # Immutable after creation


class AgentStartedData(BaseModel):
    agent_id: str
    agent_role: str
    task_id: str
    task_title: str


class AgentThoughtData(BaseModel):
    agent_id: str
    thought: str
    action: str | None = None
    action_input: dict | None = None


class ToolCallData(BaseModel):
    agent_id: str
    tool_name: str
    tool_input: dict
    timestamp: str


class ToolResultData(BaseModel):
    agent_id: str
    tool_name: str
    tool_output: str
    duration_ms: int


class AgentCompletedData(BaseModel):
    agent_id: str
    output: str
    tokens: dict = Field(default_factory=lambda: {"input": 0, "output": 0, "total": 0})


class HITLRequiredData(BaseModel):
    task_id: str
    agent_id: str
    agent_role: str
    draft_output: str
    task_description: str
    context: dict = Field(default_factory=dict)


class HITLDecisionData(BaseModel):
    approval_id: str
    decision: str  # "APPROVED" | "REJECTED"
    reason: str | None = None
    edits: str | None = None


class ErrorData(BaseModel):
    agent_id: str | None = None
    error_type: str
    error_message: str
    error_details: dict | None = None