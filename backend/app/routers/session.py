"""
Viva — Session Router
POST /api/session — create a session, commit it, then kick off question
                    generation as a FastAPI BackgroundTask.
GET  /api/session/{session_id} — get session status.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Resume, Session
from app.schemas import SessionCreateRequest, SessionDetailResponse, SessionResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["session"])


# ---------------------------------------------------------------------------
# Background question-generation task
# ---------------------------------------------------------------------------

async def _generate_initial_questions(session_id: int, resume_id: int, role: str, db: AsyncSession) -> None:
    """
    Runs synchronously before the HTTP response is sent.
    Uses the request's db session.
    """
    from app.services.retrieval import build_retrieval_queries, retrieve_chunks
    from app.services.question_generator import generate_questions
    from app.schemas import ExtractedResumeData
    from app.models import Resume, Session, Question
    from app.config import get_settings

    settings = get_settings()

    try:
            resume = await db.get(Resume, resume_id)
            if resume is None:
                logger.error("Background task: resume %d not found", resume_id)
                return

            session_row = await db.get(Session, session_id)
            if session_row is None:
                logger.error("Background task: session %d not found", session_id)
                return

            resume_data = ExtractedResumeData(**(resume.extracted_skills or {}))

            queries = await build_retrieval_queries(resume_data, role)
            chunks = await retrieve_chunks(
                queries=queries,
                db=db,
                top_k=5,
                difficulty_target=session_row.difficulty_target,
            )

            questions = await generate_questions(
                chunks=chunks,
                resume_data=resume_data,
                role=role,
                count=settings.initial_question_count,
            )

            for idx, q in enumerate(questions):
                question_row = Question(
                    session_id=session_id,
                    chunk_ids=q.chunk_ids,
                    question_text=q.question_text,
                    difficulty=q.difficulty,
                    order_index=idx,
                    is_adaptive_followup=False,
                )
                db.add(question_row)

            # Wait to commit the transaction until generation completes successfully
            logger.info(
                "Synchronously generated %d questions for session %d",
                len(questions),
                session_id,
            )

        except Exception as exc:
            logger.error(
                "Question generation failed for session %d: %s",
                session_id,
                exc,
                exc_info=True,
            )
            raise

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
    Triggers retrieval + question generation synchronously before returning.
    """
    # Verify resume exists
    resume = await db.get(Resume, body.resumeId)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume {body.resumeId} not found.",
        )

    # Create and persist the session row
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

    session_id = session_row.id
    logger.info("Session created: id=%d, resume_id=%d", session_id, resume.id)

    # Generate initial questions synchronously (in the same request session).
    # Since get_db auto-commits on success, this will commit the session and questions together.
    # We pass the active db session instead of creating a new one.
    await _generate_initial_questions(session_id, resume.id, body.role, db)

    return SessionResponse(
        id=str(session_id),
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
