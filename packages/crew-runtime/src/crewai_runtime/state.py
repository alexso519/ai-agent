"""Runtime state enum for CrewRuntime lifecycle.

Governance: Section 4 — CrewRuntime Abstraction Design
"""

from enum import Enum


class RuntimeState(str, Enum):
    """CrewRuntime lifecycle states."""

    IDLE = "IDLE"
    CONSTRUCTED = "CONSTRUCTED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"