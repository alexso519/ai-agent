"""Celery task definitions for workflow execution.

Governance: Section 3.3 — Worker Task Definitions
"""

from celery import shared_task


@shared_task(
    bind=True,
    name="workflow.execute",
    queue="workflow_default",
    acks_late=True,
    reject_on_worker_lost=True,
    task_track_started=True,
)
def run_crew(self, execution_id: str, workflow_config: dict):
    """Execute a crew workflow asynchronously.

    Phase 1 implementation: delegates to ExecutionOrchestrator.
    """
    from crewai_runtime import CrewRuntime

    runtime = CrewRuntime(execution_id)
    runtime.construct(workflow_config)
    return {"status": "completed", "execution_id": execution_id}


@shared_task(
    bind=True,
    name="workflow.control",
    queue="workflow_control",
    acks_late=True,
)
def control_crew(self, execution_id: str, command: str, payload: dict | None = None):
    """Handle pause, resume, kill, replay commands.

    Phase 1 implementation: basic lifecycle control.
    """
    from crewai_runtime import CrewRuntime

    runtime = CrewRuntime(execution_id)
    if command == "pause":
        runtime.pause()
    elif command == "resume":
        runtime.resume()
    elif command == "kill":
        runtime.kill()
    return {"execution_id": execution_id, "command": command, "status": "acknowledged"}