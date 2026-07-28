"""Screening Celery tasks."""
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
    name="app.workers.tasks.screening_tasks.screen_application",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="screening",
)
def screen_application(self, application_id: str):
    """Run AI screening for a single application in the background."""
    from app.db.session import AsyncSessionLocal
    from app.services.screening_service import ScreeningService

    async def _run():
        async with AsyncSessionLocal() as db:
            service = ScreeningService(db)
            await service.screen_application(uuid.UUID(application_id))
            logger.info("Application screened", application_id=application_id)

    try:
        _run_async(_run())
    except Exception as exc:
        logger.error("Screening task failed", application_id=application_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.tasks.screening_tasks.batch_screen_job",
    queue="screening",
)
def batch_screen_job(job_id: str):
    """Screen all pending applications for a job."""
    from app.db.session import AsyncSessionLocal
    from app.models.application import Application, ApplicationStatus
    from sqlalchemy import select

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Application).where(
                    Application.job_id == uuid.UUID(job_id),
                    Application.status == ApplicationStatus.applied,
                )
            )
            apps = result.scalars().all()
            for app in apps:
                screen_application.delay(str(app.id))
            logger.info("Batch screening queued", job_id=job_id, count=len(apps))

    _run_async(_run())
