"""Celery application configuration for the CrewAI worker.

Governance: Section 5 — Celery Orchestration Model
"""

from celery import Celery

celery_app = Celery("crewai_worker")

celery_app.config_from_object(
    {
        "broker_url": "redis://redis:6379/0",
        "result_backend": "redis://redis:6379/1",
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "task_track_started": True,
        "task_soft_time_limit": 3600,
        "task_time_limit": 3900,
        "result_expires": 86400,
    }
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["worker.tasks"])