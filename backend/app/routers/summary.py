"""
Viva — Summary Router
GET /api/session/{session_id}/summary — generate and return session summary.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Answer, Question, Session
from app.schemas import SummaryResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["summary"])

_DIFFICULTY_INT = {"Fundamentals": 1, "Intermediate": 2, "Advanced": 3}


@router.get(
    "/session/{session_token}/summary",
    response_model=SummaryResponse,
    summary="Generate a structured session summary from stored Q&A records",
)
async def get_summary(
    session_token: str,
    db: AsyncSession = Depends(get_db),
) -> SummaryResponse:
    """
    Generates a structured summary of the completed interview session.
    Reads only from stored Q&A records — never re-fetches or regenerates questions.

    Requires the session to have at least one answered question.
    """
    from app.utils.session_lookup import get_session_by_token
    session_row = await get_session_by_token(session_token, db)
    session_id = session_row.id

    # Fetch all answered questions with their answers
    result = await db.execute(
        select(Question, Answer)
        .join(Answer, Answer.question_id == Question.id)
        .where(Question.session_id == session_id)
        .order_by(Question.order_index)
    )
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No answered questions found. Complete at least one question before requesting a summary.",
        )

    # Build QA records for the Groq summary call
    from app.services.summary_generator import generate_summary, QARecord
    qa_records = [
        QARecord(
            question_text=q.question_text,
            answer_text=a.answer_text,
            quality_score=a.quality_score or "ok",
            difficulty=q.difficulty,
        )
        for q, a in rows
    ]

    summary_data = await generate_summary(session_id=session_id, qa_records=qa_records)

    # Build transcript items with source info
    from app.schemas import TranscriptItem, QuestionResponse, SourceInfo
    from app.models import ChunkSource

    transcript_items = []
    for q, a in rows:
        # Resolve primary source
        source = SourceInfo(book="Knowledge Base", chapter="See source", page=None, similarity=0.85)
        if q.chunk_ids:
            src_result = await db.execute(
                select(ChunkSource).where(ChunkSource.chunk_id == q.chunk_ids[0]).limit(1)
            )
            src_row = src_result.scalar_one_or_none()
            if src_row:
                book_display = {
                    "mitchell": "Machine Learning (Mitchell)",
                    "bishop": "Pattern Recognition and Machine Learning (Bishop)",
                    "burkov": "The Hundred-Page Machine Learning Book (Burkov)",
                }.get(src_row.book, src_row.book)
                source = SourceInfo(
                    book=book_display,
                    chapter=src_row.chapter or "Unknown Chapter",
                    page=src_row.page,
                    similarity=0.85,
                )

        transcript_items.append(
            TranscriptItem(
                question=QuestionResponse(
                    id=str(q.id),
                    text=q.question_text,
                    difficulty=q.difficulty,
                    source=source,
                    isAdaptiveFollowup=q.is_adaptive_followup,
                ),
                answer=a.answer_text,
                score=a.numeric_score if a.numeric_score is not None else 50,
            )
        )

    from app.schemas import PerformanceSeriesItem
    performance_series = []
    for q, a in rows:
        performance_series.append(
            PerformanceSeriesItem(
                orderIndex=q.order_index,
                difficulty=q.difficulty,
                questionText=q.question_text,
                answerText=a.answer_text,
                numericScore=a.numeric_score if a.numeric_score is not None else 50,
                qualityScore=a.quality_score or "ok",
                scoreReasoning=a.score_reasoning or "",
                chunkIds=q.chunk_ids or [],
            )
        )

    # Difficulty trend: sequence of 1/2/3
    difficulty_trend = [_DIFFICULTY_INT.get(q.difficulty, 2) for q, _ in rows]

    # Score distribution
    score_dist = {"weak": 0, "ok": 0, "strong": 0}
    for _, a in rows:
        key = a.quality_score or "ok"
        score_dist[key] = score_dist.get(key, 0) + 1

    from app.schemas import ScoreDistribution
    return SummaryResponse(
        overallAssessment=summary_data.overall_assessment,
        strengths=summary_data.strengths,
        gaps=summary_data.gaps,
        scoreDistribution=ScoreDistribution(**score_dist),
        difficultyTrend=difficulty_trend,
        transcript=transcript_items,
        performanceSeries=performance_series,
    )
