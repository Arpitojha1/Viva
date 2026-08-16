"""
Viva — Session Router
POST /api/session — create a session, run retrieval, generate initial questions.
GET  /api/session/{session_id} — get session status.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Resume, Session
from app.schemas import SessionCreateRequest, SessionDetailResponse, SessionResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["session"])


@router.post(
    "/session",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an interview session and pre-generate initial questions",
)
async def create_session(
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    Create a new interview session for a previously uploaded resume.
    Triggers retrieval + question generation (5 initial questions).
    """
    # Verify resume exists
    resume = await db.get(Resume, body.resumeId)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume {body.resumeId} not found.",
        )

    # Create session row
    session_row = Session(
        resume_id=resume.id,
        user_id=None,
        role=body.role,
        difficulty_target=0.5,
        status="active",
    )
    db.add(session_row)
    await db.flush()
    await db.refresh(session_row)

    logger.info("Session created: id=%d, resume_id=%d", session_row.id, resume.id)

    # Generate initial questions in the background after returning the session ID.
    # We trigger this as a deferred task so the frontend gets the session ID fast.
    # Questions are generated before the first /next-question call arrives.
    try:
        from app.services.retrieval import build_retrieval_queries, retrieve_chunks
        from app.services.question_generator import generate_questions
        from app.config import get_settings
        import json

        settings = get_settings()
        resume_data_dict = resume.extracted_skills
        from app.schemas import ExtractedResumeData
        resume_data = ExtractedResumeData(**resume_data_dict)

        queries = await build_retrieval_queries(resume_data, body.role)
        chunks = await retrieve_chunks(
            queries=queries,
            db=db,
            top_k=5,
            difficulty_target=session_row.difficulty_target,
        )

        questions = await generate_questions(
            chunks=chunks,
            resume_data=resume_data,
            role=body.role,
            count=settings.initial_question_count,
        )

        from app.models import Question
        for idx, q in enumerate(questions):
            question_row = Question(
                session_id=session_row.id,
                chunk_ids=q.chunk_ids,
                question_text=q.question_text,
                difficulty=q.difficulty,
                order_index=idx,
                is_adaptive_followup=False,
            )
            db.add(question_row)

        logger.info(
            "Generated %d initial questions for session %d", len(questions), session_row.id
        )
    except Exception as exc:
        logger.error("Question generation failed for session %d: %s", session_row.id, exc, exc_info=True)
        # Don't fail the session creation — the interview can still start,
        # but /next-question will return an error if no questions exist.

    return SessionResponse(
        id=str(session_row.id),
        role=session_row.role,
        status=session_row.status,
    )


@router.get(
    "/session/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get session status and progress",
)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    session_row = await db.get(Session, session_id)
    if session_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )

    from sqlalchemy import select, func
    from app.models import Question, Answer

    total_q_result = await db.execute(
        select(func.count()).where(Question.session_id == session_id)
    )
    total_questions = total_q_result.scalar_one()

    answered_result = await db.execute(
        select(func.count())
        .select_from(Answer)
        .join(Question, Question.id == Answer.question_id)
        .where(Question.session_id == session_id)
    )
    answered_count = answered_result.scalar_one()

    return SessionDetailResponse(
        id=str(session_row.id),
        role=session_row.role,
        status=session_row.status,
        totalQuestions=total_questions,
        answeredCount=answered_count,
        createdAt=session_row.created_at.isoformat(),
    )
