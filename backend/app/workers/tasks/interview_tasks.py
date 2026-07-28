"""Interview Celery tasks."""
from __future__ import annotations
import asyncio
import uuid
from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.workers.tasks.interview_tasks.generate_interview_report",
    bind=True,
    max_retries=2,
    queue="interviews",
)
def generate_interview_report(self, interview_id: str):
    """Generate final interview report after completion."""
    from app.db.session import AsyncSessionLocal
    from app.services.interview_service import InterviewService

    async def _run():
        async with AsyncSessionLocal() as db:
            service = InterviewService(db)
            report = await service.get_interview_report(uuid.UUID(interview_id))
            logger.info("Interview report generated", interview_id=interview_id)
            return report

    try:
        _run_async(_run())
    except Exception as exc:
        logger.error("Report generation failed", interview_id=interview_id, error=str(exc))
        raise self.retry(exc=exc)
