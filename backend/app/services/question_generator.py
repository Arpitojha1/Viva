"""
Viva — Question Generator Service
Generates interview questions grounded in retrieved knowledge-base chunks.
Uses Groq (70b model) with structured JSON output.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import get_settings
from app.schemas import ExtractedResumeData
from app.services.retrieval import ChunkResult
from app.utils.llm_client import chat_completion

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class GeneratedQuestion:
    question_text: str
    chunk_ids: List[int]
    difficulty: str  # 'Fundamentals' | 'Intermediate' | 'Advanced'
    order_index: int = 0


_GENERATION_PROMPT = """You are an expert ML/AI interviewer. Generate {count} interview questions for a candidate applying for the role of {role}.

Candidate background:
- Skills: {skills}
- Technologies: {technologies}
- Experience level: {experience_level}
- Domain exposure: {domains}

Use the following Knowledge Base excerpts as the ONLY grounding source for your questions. Each question MUST be directly inspired by and testable from these excerpts. Do NOT generate generic or templated questions.

Knowledge Base Excerpts:
{chunks}

Requirements:
- Questions should assess CONCEPTUAL UNDERSTANDING and APPLIED THINKING, not rote definitions.
- Difficulty should match the candidate's level ({experience_level}): focus on {difficulty_focus}.
- Each question should target a DIFFERENT concept from the excerpts.
- Questions should be open-ended and require 2-4 sentences to answer well.
- Avoid yes/no questions or trivial recall questions.

Return ONLY a valid JSON array:
[
  {{"question": "...", "difficulty": "Fundamentals" | "Intermediate" | "Advanced"}},
  ...
]"""


async def generate_questions(
    chunks: List[ChunkResult],
    resume_data: ExtractedResumeData,
    role: str,
    count: int = 5,
) -> List[GeneratedQuestion]:
    """
    Generate `count` interview questions grounded in the provided chunks.

    Returns a list of GeneratedQuestion. Falls back to a minimal default set
    if Groq call fails.
    """
    if not chunks:
        logger.warning("No chunks provided for question generation — using fallback")
        return _fallback_questions(count)

    difficulty_focus = {
        "junior": "foundational concepts and basic applied skills",
        "mid": "intermediate concepts, trade-offs, and practical application",
        "senior": "advanced theory, system design, and nuanced trade-offs",
    }.get(resume_data.experience_level, "intermediate concepts and application")

    # Format chunk excerpts (truncate each to ~400 chars for token budget)
    chunk_texts = []
    for i, chunk in enumerate(chunks[:8], start=1):
        source = f"[{chunk.book.upper()} | {chunk.chapter or 'Unknown Chapter'} | p.{chunk.page}]"
        excerpt = chunk.content[:400].replace("\n", " ").strip()
        chunk_texts.append(f"Excerpt {i} {source}:\n{excerpt}")

    chunks_formatted = "\n\n".join(chunk_texts)

    prompt = _GENERATION_PROMPT.format(
        count=count,
        role=role,
        skills=", ".join(resume_data.skills[:8]) or "machine learning",
        technologies=", ".join(resume_data.technologies[:8]) or "Python",
        experience_level=resume_data.experience_level,
        domains=", ".join(resume_data.domain_exposure[:6]) or "ML/AI",
        chunks=chunks_formatted,
        difficulty_focus=difficulty_focus,
    )

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_model_generation,
            temperature=0.75,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        parsed = json.loads(response)
        # Handle both {"questions": [...]} and [...]
        if isinstance(parsed, list):
            q_list = parsed
        elif isinstance(parsed, dict):
            q_list = next((v for v in parsed.values() if isinstance(v, list)), [])
        else:
            q_list = []

        questions = []
        # Use chunks' IDs in round-robin per question for traceability
        chunk_ids = [c.chunk_id for c in chunks]

        for idx, item in enumerate(q_list[:count]):
            if not isinstance(item, dict) or "question" not in item:
                continue
            # Assign 2 chunk IDs per question (the two most relevant for that position)
            assigned_chunk_ids = chunk_ids[idx : idx + 2] or chunk_ids[:2]

            questions.append(
                GeneratedQuestion(
                    question_text=item["question"].strip(),
                    chunk_ids=assigned_chunk_ids,
                    difficulty=item.get("difficulty", "Intermediate"),
                    order_index=idx,
                )
            )

        if questions:
            logger.info("Generated %d questions (requested %d)", len(questions), count)
            return questions

    except Exception as exc:
        logger.error("Question generation failed: %s", exc, exc_info=True)

    return _fallback_questions(count)


async def generate_adaptive_followup(
    previous_question: str,
    previous_answer: str,
    score: str,
    difficulty_target: float,
    chunks: List[ChunkResult],
    resume_data: ExtractedResumeData,
) -> Optional[GeneratedQuestion]:
    """
    Generate a single adaptive follow-up question based on the candidate's answer quality.

    If score='strong': probe deeper into the same topic (harder chunk, more nuanced question).
    If score='weak': pivot to foundational concepts in the same area.
    """
    if not chunks:
        return None

    direction = "deeper and more nuanced" if score == "strong" else "more foundational and clarifying"
    score_context = (
        "The candidate answered very well, demonstrating strong understanding."
        if score == "strong"
        else "The candidate's answer showed gaps or confusion in their understanding."
    )

    # Use chunks already biased by difficulty_target from retrieve_chunks
    chunk_texts = []
    for i, chunk in enumerate(chunks[:4], start=1):
        source = f"[{chunk.book.upper()} | {chunk.chapter or 'Unknown'} | p.{chunk.page}]"
        excerpt = chunk.content[:350].replace("\n", " ").strip()
        chunk_texts.append(f"Excerpt {i} {source}:\n{excerpt}")

    chunks_formatted = "\n\n".join(chunk_texts)

    prompt = f"""You are an ML/AI interviewer conducting an adaptive interview.

Previous question: {previous_question}
Candidate's answer: {previous_answer[:600]}

Assessment: {score_context}

Generate exactly ONE follow-up question that goes {direction} into this topic.
Ground the question in these Knowledge Base excerpts:

{chunks_formatted}

The question should:
- Build directly on the previous exchange
- Be {'more advanced and nuanced' if score == 'strong' else 'more foundational, probing the gaps'}
- Require a substantive answer (2-4 sentences)
- Not repeat what was already asked

Return ONLY a JSON object:
{{"question": "...", "difficulty": "{'Advanced' if score == 'strong' else 'Fundamentals'}"}}"""

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_model_generation,
            temperature=0.7,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response)
        if isinstance(parsed, dict) and "question" in parsed:
            chunk_ids = [c.chunk_id for c in chunks[:2]]
            return GeneratedQuestion(
                question_text=parsed["question"].strip(),
                chunk_ids=chunk_ids,
                difficulty=parsed.get("difficulty", "Advanced" if score == "strong" else "Fundamentals"),
            )
    except Exception as exc:
        logger.error("Adaptive follow-up generation failed: %s", exc)

    return None


def _fallback_questions(count: int) -> List[GeneratedQuestion]:
    """Minimal fallback if Groq is unavailable. Should never reach production."""
    fallbacks = [
        ("Explain the bias-variance tradeoff and how it influences model selection.", "Fundamentals"),
        ("How does gradient descent optimization work, and what are common variants?", "Intermediate"),
        ("Describe the role of regularization techniques like L1 and L2 in preventing overfitting.", "Intermediate"),
        ("What is the difference between generative and discriminative models?", "Fundamentals"),
        ("How would you approach feature selection for a high-dimensional dataset?", "Advanced"),
    ]
    return [
        GeneratedQuestion(
            question_text=q,
            chunk_ids=[],
            difficulty=d,
            order_index=i,
        )
        for i, (q, d) in enumerate(fallbacks[:count])
    ]
