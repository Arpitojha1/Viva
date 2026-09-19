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

import time
from typing import Dict, Tuple

# TTL Cache for summaries: { session_token: (expiry_timestamp, SummaryResponse) }
# Explicit TTL: 1 hour (3600 seconds).
# Invalidation strategy: Time-based expiry, plus LRU-style eviction if cache exceeds 1000 items to prevent memory leaks.
_SUMMARY_CACHE: Dict[str, Tuple[float, "SummaryResponse"]] = {}
_CACHE_TTL_SECONDS = 3600
_MAX_CACHE_SIZE = 1000

def _get_cached_summary(token: str):
    if token in _SUMMARY_CACHE:
        expiry, response = _SUMMARY_CACHE[token]
        if time.time() < expiry:
            return response
        else:
            del _SUMMARY_CACHE[token]
    return None

def _set_cached_summary(token: str, response: "SummaryResponse"):
    if len(_SUMMARY_CACHE) >= _MAX_CACHE_SIZE:
        # Simple LRU-ish eviction: clear oldest 20%
        oldest = sorted(_SUMMARY_CACHE.keys(), key=lambda k: _SUMMARY_CACHE[k][0])[: _MAX_CACHE_SIZE // 5]
        for k in oldest:
            _SUMMARY_CACHE.pop(k, None)
    _SUMMARY_CACHE[token] = (time.time() + _CACHE_TTL_SECONDS, response)



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
    cached = _get_cached_summary(session_token)
    if cached:
        return cached

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

    # Batch fetch chunk sources to prevent N+1 queries
    chunk_ids_to_fetch = [q.chunk_ids[0] for q, a in rows if q.chunk_ids]
    chunk_sources_map = {}
    if chunk_ids_to_fetch:
        src_result = await db.execute(
            select(ChunkSource).where(ChunkSource.chunk_id.in_(chunk_ids_to_fetch))
        )
        for src_row in src_result.scalars():
            if src_row.chunk_id not in chunk_sources_map:
                chunk_sources_map[src_row.chunk_id] = src_row

    transcript_items = []
    for q, a in rows:
        # Resolve primary source
        source = SourceInfo(book="Knowledge Base", chapter="See source", page=None, similarity=0.85)
        if q.chunk_ids:
            src_row = chunk_sources_map.get(q.chunk_ids[0])
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
    response = SummaryResponse(
        overallAssessment=summary_data.overall_assessment,
        strengths=summary_data.strengths,
        gaps=summary_data.gaps,
        scoreDistribution=ScoreDistribution(**score_dist),
        difficultyTrend=difficulty_trend,
        transcript=transcript_items,
        performanceSeries=performance_series,
    )
    _set_cached_summary(session_token, response)
    return response
