"""
Analytics API routes.
GET /api/v1/analytics/recruiter-dashboard
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_recruiter
from app.db.session import get_db
from app.models.application import Application, ApplicationStatus, Interview, InterviewStatus
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas import APIResponse, RecruiterDashboardOut

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/recruiter-dashboard",
    response_model=APIResponse,
    summary="Get recruiter dashboard statistics",
)
async def recruiter_dashboard(
    current_user: Annotated[User, Depends(get_current_recruiter)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    # Active jobs count
    result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.active)
    )
    active_jobs = result.scalar() or 0

    # Total applicants
    result = await db.execute(select(func.count(Application.id)))
    total_applicants = result.scalar() or 0

    # Screened
    result = await db.execute(
        select(func.count(Application.id)).where(
            Application.status.in_([
                ApplicationStatus.screened,
                ApplicationStatus.shortlisted,
                ApplicationStatus.interview_invited,
            ])
        )
    )
    candidates_screened = result.scalar() or 0

    # Awaiting review
    result = await db.execute(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.human_review
        )
    )
    awaiting_review = result.scalar() or 0

    # Interviews
    result = await db.execute(
        select(func.count(Interview.id)).where(
            Interview.status.in_([InterviewStatus.pending, InterviewStatus.in_progress])
        )
    )
    interviews_scheduled = result.scalar() or 0

    result = await db.execute(
        select(func.count(Interview.id)).where(
            Interview.status == InterviewStatus.completed
        )
    )
    interviews_completed = result.scalar() or 0

    dashboard = RecruiterDashboardOut(
        active_jobs=active_jobs,
        total_applicants=total_applicants,
        candidates_screened=candidates_screened,
        candidates_awaiting_review=awaiting_review,
        interviews_scheduled=interviews_scheduled,
        interviews_completed=interviews_completed,
    )

    return APIResponse(data=dashboard.model_dump())
