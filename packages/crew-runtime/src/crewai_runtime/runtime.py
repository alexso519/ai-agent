"""Core CrewRuntime abstraction wrapping CrewAI execution.

Governance: Section 4 — CrewRuntime Abstraction Design
Thread-safety: NOT thread-safe. Each instance for exactly one execution.
"""

from typing import AsyncIterator

from crewai_runtime.state import RuntimeState


class CrewRuntime:
    """Central abstraction wrapping CrewAI execution.

    Responsibilities:
    - Dynamic crew construction from config
    - Managed execution with lifecycle control
    - Event capture via callback interceptor
    - Checkpoint save/restore at agent boundaries
    - Memory bridge operations
    - Graceful pause/resume/kill
    """

    def __init__(self, execution_id: str) -> None:
        self._execution_id = execution_id
        self._state: RuntimeState = RuntimeState.IDLE

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def state(self) -> RuntimeState:
        return self._state

    def construct(self, config: dict) -> None:
        """Phase 1: Build a CrewAI Crew from configuration.

        Args:
            config: Workflow configuration with agents, tasks, tools
        """
        self._state = RuntimeState.CONSTRUCTED

    async def execute(self) -> AsyncIterator[dict]:
        """Phase 2: Execute the constructed Crew.

        Yields typed execution events for the orchestrator to publish.
        """
        self._state = RuntimeState.RUNNING
        yield {"type": "WORKFLOW_STARTED", "execution_id": self._execution_id}
        self._state = RuntimeState.COMPLETED

    def pause(self) -> None:
        """Signal the runtime to pause at the next safe boundary."""
        self._state = RuntimeState.PAUSED

    def resume(self) -> None:
        """Resume execution from a saved checkpoint."""
        self._state = RuntimeState.RUNNING

    def kill(self) -> None:
        """Immediately terminate execution."""
        self._state = RuntimeState.CANCELLED