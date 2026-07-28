"""
Job management routes.
POST   /api/v1/jobs                          — Create job
GET    /api/v1/jobs                          — List jobs for org
GET    /api/v1/jobs/{job_id}                 — Get job detail
PATCH  /api/v1/jobs/{job_id}                 — Update job
DELETE /api/v1/jobs/{job_id}                 — Archive job
POST   /api/v1/jobs/{job_id}/analyze-description — AI JD analysis
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import get_current_recruiter, verify_org_membership
from app.db.session import get_db
from app.models.job import Job, JobRequirement, JobStatus
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas import JobCreate, JobOut, JobUpdate, JDAnalyzeRequest, PaginatedResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


async def _get_job_or_404(job_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Job:
    """Get a job and verify it belongs to the organization."""
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.requirements))
        .where(Job.id == job_id, Job.organization_id == org_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post(
    "",
    response_model=JobOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job posting",
)
async def create_job(
    payload: JobCreate,
    organization_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Job:
    await verify_org_membership(current_user, organization_id, db)

    job = Job(
        organization_id=organization_id,
        created_by=current_user.id,
        title=payload.title,
        description=payload.description,
        department=payload.department,
        location=payload.location,
        employment_type=payload.employment_type,
        status=JobStatus.draft,
    )
    db.add(job)
    await db.flush()

    for req_in in payload.requirements:
        req = JobRequirement(
            job_id=job.id,
            requirement_type=req_in.requirement_type,
            name=req_in.name,
            importance=req_in.importance,
            weight=req_in.weight,
            minimum_level=req_in.minimum_level,
        )
        db.add(req)

    await db.refresh(job, ["requirements"])
    return job


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List all jobs for the current organization",
)
async def list_jobs(
    organization_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: JobStatus | None = Query(default=None, alias="status"),
) -> PaginatedResponse:
    await verify_org_membership(current_user, organization_id, db)

    query = select(Job).where(Job.organization_id == organization_id)
    if status_filter:
        query = query.where(Job.status == status_filter)

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.options(selectinload(Job.requirements))
    result = await db.execute(query)
    jobs = result.scalars().all()

    return PaginatedResponse(
        items=[JobOut.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/{job_id}",
    response_model=JobOut,
    summary="Get a single job by ID",
)
async def get_job(
    job_id: uuid.UUID,
    organization_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Job:
    await verify_org_membership(current_user, organization_id, db)
    return await _get_job_or_404(job_id, organization_id, db)


@router.patch(
    "/{job_id}",
    response_model=JobOut,
    summary="Update a job posting",
)
async def update_job(
    job_id: uuid.UUID,
    organization_id: uuid.UUID,
    payload: JobUpdate,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Job:
    await verify_org_membership(current_user, organization_id, db)
    job = await _get_job_or_404(job_id, organization_id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive a job posting",
)
async def delete_job(
    job_id: uuid.UUID,
    organization_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await verify_org_membership(current_user, organization_id, db)
    job = await _get_job_or_404(job_id, organization_id, db)
    job.status = JobStatus.archived


@router.post(
    "/{job_id}/analyze-description",
    summary="AI-powered analysis of job description to extract requirements",
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_job_description(
    job_id: uuid.UUID,
    organization_id: uuid.UUID,
    payload: JDAnalyzeRequest,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await verify_org_membership(current_user, organization_id, db)
    await _get_job_or_404(job_id, organization_id, db)

    # TODO Phase 6: Dispatch JD analysis LangGraph workflow via Celery
    # For now return accepted with a placeholder workflow ID
    return {
        "message": "JD analysis queued",
        "job_id": str(job_id),
        "status": "queued",
    }
