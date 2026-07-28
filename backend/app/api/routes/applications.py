"""
Applications API routes.
POST /api/v1/applications
GET  /api/v1/jobs/{job_id}/applications
POST /api/v1/applications/{application_id}/screen
GET  /api/v1/applications/{application_id}/screening
"""
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import get_current_recruiter, get_current_user
from app.db.session import get_db
from app.models.application import Application, ApplicationStatus, ScreeningResult
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.user import User
from app.schemas import (
    APIResponse,
    ApplicationCreate,
    ApplicationOut,
    ScreeningResultOut,
)
from app.services.screening_service import ScreeningService

router = APIRouter(tags=["Applications"])


@router.post(
    "/applications",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application (assign candidate to job)",
)
async def create_application(
    payload: ApplicationCreate,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    # Verify candidate exists
    candidate = await db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Verify job exists
    job = await db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for duplicate
    result = await db.execute(
        select(Application).where(
            Application.candidate_id == payload.candidate_id,
            Application.job_id == payload.job_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application already exists for this candidate and job",
        )

    application = Application(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        status=ApplicationStatus.applied,
    )
    db.add(application)
    await db.flush()

    return APIResponse(
        message="Application created",
        data=ApplicationOut.model_validate(application).model_dump(),
    )


@router.get(
    "/jobs/{job_id}/applications",
    response_model=APIResponse,
    summary="List all applications for a job",
)
async def list_job_applications(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    result = await db.execute(
        select(Application)
        .where(Application.job_id == job_id)
        .options(selectinload(Application.candidate))
        .order_by(Application.created_at.desc())
    )
    applications = result.scalars().all()

    data = []
    for app in applications:
        app_data = ApplicationOut.model_validate(app).model_dump()
        app_data["candidate_name"] = app.candidate.full_name
        app_data["candidate_email"] = app.candidate.email
        data.append(app_data)

    return APIResponse(data=data)


@router.post(
    "/applications/{application_id}/screen",
    response_model=APIResponse,
    summary="Run AI screening on an application",
)
async def screen_application(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    service = ScreeningService(db)
    screening = await service.screen_application(application_id)

    return APIResponse(
        message="Screening completed",
        data=ScreeningResultOut.model_validate(screening).model_dump(),
    )


@router.get(
    "/applications/{application_id}/screening",
    response_model=APIResponse,
    summary="Get screening result for an application",
)
async def get_screening(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    result = await db.execute(
        select(ScreeningResult).where(
            ScreeningResult.application_id == application_id
        )
    )
    screening = result.scalar_one_or_none()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening result not found")

    return APIResponse(
        data=ScreeningResultOut.model_validate(screening).model_dump()
    )
