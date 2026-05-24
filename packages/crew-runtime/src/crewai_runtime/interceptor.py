"""CallbackInterceptor — Captures CrewAI execution events and translates them to typed system events.

Governance: Section 4.3 — CallbackInterceptor
"""


class CallbackInterceptor:
    """Intercepts all CrewAI execution callbacks and translates them
    to typed system events published via Redis Pub/Sub.

    This is the critical bridge between CrewAI's internal execution
    and the observability pipeline.

    Captured events:
    - agent.start / agent.end
    - task.start / task.end / task.progress
    - tool.start / tool.end / tool.error
    - llm.call / llm.response (token tracking)
    - step.start / step.end
    - error events
    """

    def __init__(self, execution_id: str) -> None:
        self._execution_id = execution_id
        self._step_counter = 0

    def on_agent_start(self, agent: str, task: str) -> None:
        """Called when an agent begins executing a task."""
        self._step_counter += 1

    def on_agent_action(self, agent: str, action: str, action_input: dict) -> None:
        """Called when an agent selects and performs an action."""
        pass

    def on_tool_start(self, agent: str, tool: str, input_data: dict) -> None:
        """Called when a tool call begins."""
        pass

    def on_tool_end(self, agent: str, tool: str, output: str, duration_ms: int) -> None:
        """Called when a tool call completes."""
        pass

    def on_agent_end(self, agent: str, output: str) -> None:
        """Called when an agent completes its task."""
        pass

    def on_error(self, error: Exception, agent: str | None = None) -> None:
        """Called when an error occurs during execution."""
        pass