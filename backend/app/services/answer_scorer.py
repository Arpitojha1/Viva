"""
Viva — Answer Scorer Service
Lightweight Groq call (8b model) to score candidate answers as weak/ok/strong.
"""
import json
import logging
from dataclasses import dataclass
from typing import List

from app.config import get_settings
from app.utils.llm_client import chat_completion

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AnswerScore:
    score: str      # 'weak' | 'ok' | 'strong'
    reasoning: str  # Brief explanation (stored in DB for debugging/summary)


_SCORING_PROMPT = """You are an expert ML/AI interviewer evaluating a candidate's answer.

Question: {question}

Candidate's Answer: {answer}

Reference Context (from knowledge base):
{context}

Score the answer as one of:
- "weak": Answer is incorrect, very incomplete, shows fundamental misunderstanding, or is essentially empty.
- "ok": Answer is partially correct, covers some key points but misses important aspects or lacks depth.
- "strong": Answer is accurate, complete, demonstrates clear understanding, and shows applied thinking.

Return ONLY a JSON object:
{{"score": "weak" | "ok" | "strong", "reasoning": "1-2 sentence explanation"}}"""


async def score_answer(
    question_text: str,
    answer_text: str,
    source_chunks: List[str],
) -> AnswerScore:
    """
    Score a candidate's answer using Groq's lightweight 8b model.

    Args:
        question_text: The interview question that was asked.
        answer_text: The candidate's answer.
        source_chunks: Relevant knowledge-base chunk content for grounding the score.

    Returns:
        AnswerScore with score ('weak'|'ok'|'strong') and brief reasoning.
    """
    context = "\n\n".join(source_chunks[:2]) if source_chunks else "No reference context available."
    # Truncate answer to stay within token budget for the 8b model
    truncated_answer = answer_text[:1500]
    truncated_context = context[:600]

    prompt = _SCORING_PROMPT.format(
        question=question_text,
        answer=truncated_answer,
        context=truncated_context,
    )

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_model_scoring,  # llama-3.1-8b-instant
            temperature=0.1,  # Very low temp: we want consistent, deterministic scoring
            max_tokens=150,
            response_format={"type": "json_object"},
        )

        parsed = json.loads(response)
        score_val = parsed.get("score", "ok").lower().strip()
        if score_val not in ("weak", "ok", "strong"):
            logger.warning("Unexpected score value from Groq: %s — defaulting to 'ok'", score_val)
            score_val = "ok"

        reasoning = parsed.get("reasoning", "Score assigned by automated evaluator.")

        logger.info("Answer scored: %s", score_val)
        return AnswerScore(score=score_val, reasoning=reasoning)

    except Exception as exc:
        logger.error("Answer scoring failed: %s — defaulting to 'ok'", exc)
        return AnswerScore(score="ok", reasoning="Scoring unavailable; default score applied.")
