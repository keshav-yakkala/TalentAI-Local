"""
Resume upload routes.
POST /api/v1/resumes              — Upload single resume
POST /api/v1/resumes/bulk         — Upload multiple resumes (queued)
GET  /api/v1/resumes/{resume_id}  — Get resume details
GET  /api/v1/resumes/{resume_id}/processing-status — Check processing status
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_recruiter, verify_org_membership
from app.core.config import settings
from app.core.exceptions import FileTooLargeError, UnsupportedFileError
from app.db.session import get_db
from app.models.candidate import Candidate, ParsingStatus, Resume
from app.models.user import User
from app.schemas import ProcessingStatusOut, ResumeOut

router = APIRouter(prefix="/resumes", tags=["Resumes"])

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _validate_file(file: UploadFile) -> None:
    """Validate MIME type and file size."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' is not supported. Allowed: PDF, DOCX, TXT",
        )


@router.post(
    "",
    response_model=ResumeOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a single resume for processing",
)
async def upload_resume(
    organization_id: uuid.UUID,
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_recruiter)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> Resume:
    await verify_org_membership(current_user, organization_id, db)
    _validate_file(file)

    # Read and check size
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Verify candidate exists
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # TODO Phase 3+: Save file via StorageService
    file_path = f"{settings.UPLOAD_DIR}/{uuid.uuid4()}{ALLOWED_MIME_TYPES[file.content_type]}"

    resume = Resume(
        candidate_id=candidate_id,
        file_path=file_path,
        original_filename=file.filename or "resume",
        mime_type=file.content_type,
        parsing_status=ParsingStatus.pending,
    )
    db.add(resume)
    await db.flush()

    # TODO Phase 7: Dispatch resume ingestion LangGraph workflow via Celery
    # from app.workers.tasks.resume_tasks import process_resume
    # process_resume.delay(str(resume.id), str(organization_id), content)

    return resume


@router.post(
    "/bulk",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload multiple resumes for batch processing",
)
async def upload_resumes_bulk(
    organization_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    current_user: Annotated[User, Depends(get_current_recruiter)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict:
    await verify_org_membership(current_user, organization_id, db)

    if len(files) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 files per bulk upload request",
        )

    job_id = str(uuid.uuid4())

    # TODO Phase 11: Dispatch batch processing via Celery
    # Each file creates its own task so one failure doesn't affect others

    return {
        "message": f"{len(files)} resumes queued for processing",
        "batch_job_id": job_id,
        "file_count": len(files),
        "status": "queued",
    }


@router.get(
    "/{resume_id}",
    response_model=ResumeOut,
    summary="Get resume details",
)
async def get_resume(
    resume_id: uuid.UUID,
    organization_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Resume:
    await verify_org_membership(current_user, organization_id, db)

    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    return resume


@router.get(
    "/{resume_id}/processing-status",
    response_model=ProcessingStatusOut,
    summary="Check resume parsing and indexing status",
)
async def get_processing_status(
    resume_id: uuid.UUID,
    organization_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProcessingStatusOut:
    await verify_org_membership(current_user, organization_id, db)

    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    return ProcessingStatusOut(
        resume_id=resume.id,
        status=resume.parsing_status,
        extraction_confidence=resume.extraction_confidence,
    )
