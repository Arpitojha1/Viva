"""
Viva — Interview Router
GET  /api/interview/{session_id}/next-question — serve next unanswered question.
POST /api/interview/{session_id}/answer       — submit answer, score, adapt.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Answer, Question, Session
from app.schemas import (
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    QuestionResponse,
    SourceInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["interview"])

# Numeric score mapping: weak=35, ok=65, strong=90

# Difficulty level to integer (for difficultyTrend)
_DIFFICULTY_INT = {"Fundamentals": 1, "Intermediate": 2, "Advanced": 3}

# Difficulty level from difficulty_target float
def _target_to_level(target: float) -> str:
    if target < 0.35:
        return "Fundamentals"
    elif target < 0.65:
        return "Intermediate"
    else:
        return "Advanced"


async def _build_question_response(
    question: Question,
    db: AsyncSession,
    total_questions: int,
    similarity_score: float = 0.85,
) -> QuestionResponse:
    """Build the QuestionResponse, resolving the primary source from chunk_sources."""
    from sqlalchemy import text

    primary_source = SourceInfo(
        book="Knowledge Base",
        chapter="See source",
        page=None,
        similarity=similarity_score,
    )

    if question.chunk_ids:
        # Fetch the primary source for the first chunk (or the one closest to current difficulty)
        from app.models import ChunkSource
        result = await db.execute(
            select(ChunkSource)
            .where(ChunkSource.chunk_id == question.chunk_ids[0])
            .limit(1)
        )
        source_row = result.scalar_one_or_none()
        if source_row:
            book_display = {
                "mitchell": "Machine Learning (Mitchell)",
                "bishop": "Pattern Recognition and Machine Learning (Bishop)",
                "burkov": "The Hundred-Page Machine Learning Book (Burkov)",
            }.get(source_row.book, source_row.book)

            primary_source = SourceInfo(
                book=book_display,
                chapter=source_row.chapter or "Unknown Chapter",
                page=source_row.page,
                similarity=similarity_score,
            )

    return QuestionResponse(
        id=str(question.id),
        text=question.question_text,
        difficulty=question.difficulty,
        source=primary_source,
        isAdaptiveFollowup=question.is_adaptive_followup,
        totalQuestions=total_questions,
        currentIndex=question.order_index,
    )


@router.get(
    "/interview/{session_token}/next-question",
    response_model=QuestionResponse,
    summary="Get the next unanswered question in the interview",
)
async def get_next_question(
    session_token: str,
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """
    Returns the next unanswered question for this session, ordered by order_index.
    The frontend calls this with an incrementing index — we find the first question
    that doesn't have an associated answer yet.

    Returns 204 (via 404 with detail) when all questions are answered.
    """
    from app.utils.session_lookup import get_session_by_token
    session_row = await get_session_by_token(session_token, db)
    session_id = session_row.id

    # Total question count
    total_result = await db.execute(
        select(func.count()).where(Question.session_id == session_id)
    )
    total_questions = total_result.scalar_one()

    # Total answered count
    answered_result = await db.execute(
        select(func.count())
        .select_from(Answer)
        .join(Question, Question.id == Answer.question_id)
        .where(Question.session_id == session_id)
    )
    answered_count = answered_result.scalar_one()

    if session_row.status == "completed":
        if total_questions == 0 or answered_count < total_questions:
            logger.warning(
                "Inconsistent state: session %d is 'completed' but answered %d/%d questions.",
                session_id, answered_count, total_questions
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is already completed. Retrieve the summary instead.",
        )

    # Find the first question without an answer
    result = await db.execute(
        select(Question)
        .outerjoin(Answer, Answer.question_id == Question.id)
        .where(Question.session_id == session_id)
        .where(Answer.id.is_(None))
        .order_by(Question.order_index)
        .limit(1)
    )
    question = result.scalar_one_or_none()

    if question is None:
        if total_questions > 0 and answered_count == total_questions:
            # All generated questions have been answered. Durably mark session complete.
            session_row.status = "completed"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No more questions. Interview complete.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Questions not available yet or generation failed.",
            )

    return await _build_question_response(question, db, total_questions)


@router.post(
    "/interview/{session_token}/answer",
    response_model=AnswerSubmitResponse,
    summary="Submit an answer, get it scored, adapt difficulty",
)
async def submit_answer(
    session_token: str,
    body: AnswerSubmitRequest,
    db: AsyncSession = Depends(get_db),
) -> AnswerSubmitResponse:
    """
    Submit the candidate's answer to a question.
    1. Validates question belongs to this session.
    2. Scores the answer via Groq (lightweight 8b model).
    3. Updates adaptive difficulty_target.
    4. If score is 'strong' or 'weak', generates one follow-up question.
    5. Returns numeric score and next difficulty level.
    """
    from app.utils.session_lookup import get_session_by_token
    session_row = await get_session_by_token(session_token, db)
    session_id = session_row.id

    if not body.answer.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer cannot be empty.",
        )

    question_id = int(body.questionId)
    question = await db.get(Question, question_id)
    if question is None or question.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question {body.questionId} not found in session {session_token}.",
        )

    # --- Score the answer ---
    from app.services.answer_scorer import score_answer
    from app.models import ChunkSource

    # Retrieve chunk content for grounding context sent to scorer
    chunk_contents: list[str] = []
    if question.chunk_ids:
        from app.models import Chunk
        for chunk_id in question.chunk_ids[:2]:  # send up to 2 chunks as grounding context
            chunk = await db.get(Chunk, chunk_id)
            if chunk:
                chunk_contents.append(chunk.content[:800])  # truncate for token budget

    score_result = await score_answer(
        question_text=question.question_text,
        answer_text=body.answer,
        source_chunks=chunk_contents,
    )

    numeric_score = score_result.numeric_score

    # --- Store answer ---
    answer_row = Answer(
        question_id=question_id,
        answer_text=body.answer,
        quality_score=score_result.score,
        score_reasoning=score_result.reasoning,
        numeric_score=numeric_score,
    )
    db.add(answer_row)

    # --- Adaptive engine ---
    from app.services.adaptive_engine import AdaptiveEngine
    engine = AdaptiveEngine(current_target=session_row.difficulty_target)
    new_target, direction = engine.adjust(score_result.score)
    session_row.difficulty_target = new_target

    logger.info(
        "Session %d | Q%d | score=%s (%d) | difficulty %s→%.2f",
        session_id, question_id, score_result.score, numeric_score, direction, new_target
    )

    # --- Generate adaptive follow-up on 'strong' or 'weak' ---
    from app.config import get_settings
    settings = get_settings()

    # Count existing adaptive follow-ups to respect MAX_ADAPTIVE_FOLLOWUPS
    followup_count_result = await db.execute(
        select(func.count())
        .where(Question.session_id == session_id)
        .where(Question.is_adaptive_followup == True)
    )
    followup_count = followup_count_result.scalar_one()

    next_order_result = await db.execute(
        select(func.max(Question.order_index)).where(Question.session_id == session_id)
    )
    next_order_index = (next_order_result.scalar_one() or 0) + 1

    if score_result.score in ("strong", "weak") and followup_count < settings.max_adaptive_followups:
        try:
            from app.models import Resume
            from app.schemas import ExtractedResumeData
            from app.services.retrieval import retrieve_chunks
            from app.services.question_generator import generate_adaptive_followup

            resume = await db.get(Resume, session_row.resume_id)
            resume_data = ExtractedResumeData(**(resume.extracted_skills if resume else {}))

            followup_chunks = await retrieve_chunks(
                queries=[question.question_text],
                db=db,
                top_k=3,
                difficulty_target=new_target,
            )

            followup_q = await generate_adaptive_followup(
                previous_question=question.question_text,
                previous_answer=body.answer,
                score=score_result.score,
                difficulty_target=new_target,
                chunks=followup_chunks,
                resume_data=resume_data,
            )

            if followup_q:
                followup_row = Question(
                    session_id=session_id,
                    chunk_ids=followup_q.chunk_ids,
                    question_text=followup_q.question_text,
                    difficulty=followup_q.difficulty,
                    order_index=next_order_index,
                    is_adaptive_followup=True,
                )
                db.add(followup_row)
                logger.info("Adaptive follow-up generated for session %d (score=%s)", session_id, score_result.score)
        except Exception as exc:
            logger.error("Follow-up generation failed: %s", exc, exc_info=True)
            # Non-blocking: interview continues with pre-generated questions

    # Check if there are more questions (including any just-added follow-up)
    await db.flush()
    unanswered_result = await db.execute(
        select(func.count())
        .select_from(Question)
        .outerjoin(Answer, Answer.question_id == Question.id)
        .where(Question.session_id == session_id)
        .where(Answer.id.is_(None))
    )
    has_next = unanswered_result.scalar_one() > 0

    return AnswerSubmitResponse(
        score=numeric_score,
        nextDifficulty=_target_to_level(new_target),
        hasNextQuestion=has_next,
    )
