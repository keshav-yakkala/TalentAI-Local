"""
Resume processing Celery tasks (Phase 11).
Each task runs in a separate worker process — heavy AI work stays off the API thread.
"""
from __future__ import annotations

import asyncio
import uuid

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    """Helper: run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.workers.tasks.resume_tasks.process_resume",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="resume_ingestion",
)
def process_resume(self, resume_id: str, organization_id: str, file_content_b64: str):
    """
    Full resume ingestion pipeline:
    Parse → Extract structured profile → Chunk → Embed → Store in pgvector
    """
    import base64
    from app.db.session import AsyncSessionLocal
    from app.services.resume_service import ResumeParserService
    from app.models.candidate import Resume, ParsingStatus

    logger.info("Processing resume", resume_id=resume_id)

    async def _run():
        async with AsyncSessionLocal() as db:
            # Get resume record
            from sqlalchemy import select
            result = await db.execute(select(Resume).where(Resume.id == uuid.UUID(resume_id)))
            resume = result.scalar_one_or_none()
            if not resume:
                logger.error("Resume not found in task", resume_id=resume_id)
                return

            try:
                resume.parsing_status = ParsingStatus.parsing
                await db.flush()

                content = base64.b64decode(file_content_b64)
                parser = ResumeParserService()
                raw_text, confidence = await parser.parse(
                    content, resume.original_filename, resume.mime_type
                )

                resume.raw_text = raw_text
                resume.extraction_confidence = confidence
                resume.parsing_status = ParsingStatus.completed
                await db.commit()
                logger.info("Resume processed successfully", resume_id=resume_id, confidence=confidence)

            except Exception as exc:
                resume.parsing_status = ParsingStatus.failed
                await db.commit()
                logger.error("Resume processing failed", resume_id=resume_id, error=str(exc))
                raise self.retry(exc=exc)

    _run_async(_run())


@celery_app.task(
    name="app.workers.tasks.resume_tasks.cleanup_stale_workflows",
    queue="resume_ingestion",
)
def cleanup_stale_workflows():
    """Hourly cleanup of stale 'parsing' or 'extracting' status resumes."""
    from datetime import UTC, datetime, timedelta
    from app.db.session import AsyncSessionLocal
    from app.models.candidate import Resume, ParsingStatus

    async def _run():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, update
            cutoff = datetime.now(UTC) - timedelta(hours=2)
            await db.execute(
                update(Resume)
                .where(
                    Resume.parsing_status.in_([ParsingStatus.parsing, ParsingStatus.extracting]),
                    Resume.created_at < cutoff,
                )
                .values(parsing_status=ParsingStatus.failed)
            )
            await db.commit()
            logger.info("Stale workflows cleaned up")

    _run_async(_run())
