"""
Interview API routes.
POST /api/v1/applications/{application_id}/interviews
POST /api/v1/interviews/{interview_id}/start
GET  /api/v1/interviews/{interview_id}
GET  /api/v1/interviews/{interview_id}/question
POST /api/v1/interviews/{interview_id}/answers/text
GET  /api/v1/interviews/{interview_id}/report
"""
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.application import Interview, InterviewStatus
from app.models.user import User
from app.schemas import (
    APIResponse,
    InterviewOut,
    InterviewQuestionOut,
    TextAnswerRequest,
)
from app.services.interview_service import InterviewService

router = APIRouter(tags=["Interviews"])


@router.post(
    "/applications/{application_id}/interviews",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new interview for an application",
)
async def create_interview(
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    service = InterviewService(db)
    interview = await service.create_interview(application_id)
    return APIResponse(
        message="Interview created",
        data=InterviewOut.model_validate(interview).model_dump(),
    )


@router.post(
    "/interviews/{interview_id}/start",
    response_model=APIResponse,
    summary="Start an interview and generate the first question",
)
async def start_interview(
    interview_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    service = InterviewService(db)
    interview = await service.start_interview(interview_id)
    return APIResponse(
        message="Interview started",
        data=InterviewOut.model_validate(interview).model_dump(),
    )


@router.get(
    "/interviews/{interview_id}",
    response_model=APIResponse,
    summary="Get interview status",
)
async def get_interview(
    interview_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return APIResponse(
        data=InterviewOut.model_validate(interview).model_dump()
    )


@router.get(
    "/interviews/{interview_id}/question",
    response_model=APIResponse,
    summary="Get the current unanswered interview question",
)
async def get_current_question(
    interview_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    service = InterviewService(db)
    question = await service.get_current_question(interview_id)
    if not question:
        return APIResponse(
            message="No pending question",
            data=None,
        )
    return APIResponse(
        data=InterviewQuestionOut.model_validate(question).model_dump()
    )


@router.post(
    "/interviews/{interview_id}/answers/text",
    response_model=APIResponse,
    summary="Submit a text answer to the current question",
)
async def submit_text_answer(
    interview_id: uuid.UUID,
    payload: TextAnswerRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    service = InterviewService(db)
    result = await service.submit_text_answer(interview_id, payload.answer_text)
    return APIResponse(
        message="Answer submitted and evaluated",
        data=result,
    )


@router.get(
    "/interviews/{interview_id}/report",
    response_model=APIResponse,
    summary="Get the interview report",
)
async def get_report(
    interview_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIResponse:
    service = InterviewService(db)
    report = await service.get_interview_report(interview_id)
    return APIResponse(data=report)
