"""
Viva — Summary Generator Service
Generates a structured session summary from stored Q&A records using Groq.
Never re-fetches questions or answers from the knowledge base — works only
from the records passed in.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import List

from app.config import get_settings
from app.utils.llm_client import chat_completion

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class QARecord:
    question_text: str
    answer_text: str
    quality_score: str   # 'weak' | 'ok' | 'strong'
    difficulty: str      # 'Fundamentals' | 'Intermediate' | 'Advanced'


@dataclass
class SessionSummary:
    overall_assessment: str
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)


_SUMMARY_PROMPT = """You are an expert ML/AI hiring manager. Analyze the following interview session and provide a structured assessment.

Interview Transcript:
{transcript}

Based on the above, provide:
1. overallAssessment: 2-3 sentence paragraph summarizing the candidate's performance, areas of strength, and any notable gaps.
2. strengths: List of 2-4 specific technical strength areas demonstrated (concise labels, e.g. "Neural Network Architectures", "Regularization Theory").
3. gaps: List of 1-3 specific technical areas where the candidate showed gaps or uncertainty.

Return ONLY a JSON object:
{{
  "overallAssessment": "...",
  "strengths": ["...", "..."],
  "gaps": ["...", "..."]
}}"""


async def generate_summary(
    session_id: int,
    qa_records: List[QARecord],
) -> SessionSummary:
    """
    Generate a structured session summary from stored Q&A records.

    Args:
        session_id: Session ID (for logging).
        qa_records: List of QARecord from answered questions.

    Returns:
        SessionSummary with overall_assessment, strengths, gaps.
    """
    if not qa_records:
        return SessionSummary(
            overall_assessment="No questions were answered in this session.",
            strengths=[],
            gaps=["Session incomplete"],
        )

    # Format transcript for the prompt
    transcript_lines = []
    for i, record in enumerate(qa_records, start=1):
        score_display = {"weak": "⬇ Weak", "ok": "→ OK", "strong": "⬆ Strong"}.get(
            record.quality_score, "→ OK"
        )
        transcript_lines.append(
            f"Q{i} [{record.difficulty}] {record.question_text}\n"
            f"Answer: {record.answer_text[:600]}\n"
            f"Score: {score_display}"
        )

    transcript = "\n\n---\n\n".join(transcript_lines)

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": _SUMMARY_PROMPT.format(transcript=transcript)}],
            model=settings.groq_model_generation,
            temperature=0.5,
            max_tokens=600,
            response_format={"type": "json_object"},
        )

        parsed = json.loads(response)
        return SessionSummary(
            overall_assessment=parsed.get(
                "overallAssessment",
                "Summary generated from interview session.",
            ),
            strengths=parsed.get("strengths", [])[:4],
            gaps=parsed.get("gaps", [])[:3],
        )

    except Exception as exc:
        logger.error("Summary generation failed for session %d: %s", session_id, exc, exc_info=True)
        # Fallback: build a mechanical summary from scores
        strong_count = sum(1 for r in qa_records if r.quality_score == "strong")
        weak_count = sum(1 for r in qa_records if r.quality_score == "weak")
        total = len(qa_records)

        assessment = (
            f"The candidate answered {total} questions. "
            f"{strong_count} showed strong understanding, "
            f"{weak_count} showed gaps. "
            f"Manual review recommended."
        )
        return SessionSummary(
            overall_assessment=assessment,
            strengths=["See transcript for details"],
            gaps=["See transcript for details"] if weak_count > 0 else [],
        )
