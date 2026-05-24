"""CrewAI Enterprise Control Center — Crew Runtime Package

Central abstraction wrapping CrewAI execution with:
- Dynamic crew construction from config
- Managed execution with lifecycle control
- Event capture via callback interceptor
- Checkpoint save/restore at agent boundaries
- Memory bridge operations
- Graceful pause/resume/kill

Governance: Section 4 — CrewRuntime Abstraction Design
Thread-safety: NOT thread-safe. Each instance for exactly one execution.
"""

from .runtime import CrewRuntime
from .builder import CrewBuilder
from .interceptor import CallbackInterceptor
from .state import RuntimeState

__all__ = [
    "CrewRuntime",
    "CrewBuilder",
    "CallbackInterceptor",
    "RuntimeState",
]