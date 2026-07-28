"""
Celery Application (Phase 11)
Background job processing for resume ingestion, screening, and batch operations.

The original app.py ran everything synchronously in the Streamlit UI thread,
blocking the user interface during PDF parsing and LLM calls.

This implementation offloads all AI operations to Celery workers:
- resume_ingestion: Parse → Extract → Embed → Store (can take 10-60s)
- candidate_screening: Full 7-category scoring (can take 20-120s)
- batch_screening: Screen all candidates for a job
"""
from __future__ import annotations

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "talentai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.resume_tasks",
        "app.workers.tasks.screening_tasks",
        "app.workers.tasks.interview_tasks",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing — separate queues for different job types
    task_routes={
        "app.workers.tasks.resume_tasks.*": {"queue": "resume_ingestion"},
        "app.workers.tasks.screening_tasks.*": {"queue": "screening"},
        "app.workers.tasks.interview_tasks.*": {"queue": "interviews"},
    },

    # Reliability settings
    task_acks_late=True,            # Acknowledge after completion (not on delivery)
    task_reject_on_worker_lost=True,  # Re-queue on worker crash
    worker_prefetch_multiplier=1,   # One task per worker at a time (LLM calls are heavy)

    # Result expiry
    result_expires=3600,  # 1 hour

    # Retry settings
    task_max_retries=3,
    task_default_retry_delay=30,  # seconds

    # Beat schedule (periodic tasks)
    beat_schedule={
        "cleanup-stale-workflows": {
            "task": "app.workers.tasks.resume_tasks.cleanup_stale_workflows",
            "schedule": 3600.0,  # Every hour
        },
    },
)
