"""
Viva — Retrieval Service
Builds retrieval queries from resume data, queries pgvector with cosine similarity,
deduplicates results, and applies soft difficulty bias via chapter_position.
"""
import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas import ExtractedResumeData
from app.utils.embeddings import embed_query
from app.utils.llm_client import chat_completion_json

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ChunkResult:
    chunk_id: int
    content: str
    similarity: float
    book: str
    chapter: Optional[str]
    section: Optional[str]
    page: Optional[int]
    chapter_position: Optional[float]
    difficulty: str  # 'Fundamentals' | 'Intermediate' | 'Advanced'


_QUERY_BUILD_PROMPT = """You are helping to retrieve relevant Machine Learning knowledge base passages to generate interview questions for a candidate.

Candidate profile:
- Skills: {skills}
- Technologies: {technologies}
- Experience level: {experience_level}
- Domain exposure: {domains}
- Role: {role}

Generate exactly 3 concise retrieval queries (each 8-15 words) that will find the most relevant ML/AI textbook passages for evaluating this candidate. Each query should target a DIFFERENT topic area implied by their background.

Return ONLY a JSON array of 3 strings:
["query 1", "query 2", "query 3"]"""


async def build_retrieval_queries(
    resume_data: ExtractedResumeData,
    role: str,
) -> List[str]:
    """
    Generate 3 topically distinct retrieval queries from resume data and role.
    Falls back to generic ML queries if Groq call fails.
    """
    prompt = _QUERY_BUILD_PROMPT.format(
        skills=", ".join(resume_data.skills[:10]) or "general ML",
        technologies=", ".join(resume_data.technologies[:10]) or "Python, scikit-learn",
        experience_level=resume_data.experience_level,
        domains=", ".join(resume_data.domain_exposure[:8]) or "machine learning",
        role=role,
    )

    try:
        parsed = await chat_completion_json(
            messages=[{"role": "user", "content": prompt}],
            model=settings.groq_model_generation,
            temperature=0.4,
            max_tokens=800,
        )

        # Handle both {"queries": [...]} and [...]
        if isinstance(parsed, list):
            queries = parsed
        elif isinstance(parsed, dict):
            # Find first list value in the response
            queries = next(
                (v for v in parsed.values() if isinstance(v, list)), []
            )
        else:
            queries = []

        queries = [q for q in queries if isinstance(q, str) and q.strip()][:3]
        if queries:
            logger.info("Built %d retrieval queries from resume", len(queries))
            return queries
    except Exception as exc:
        logger.warning("Query building via Groq failed (%s), using fallback queries", exc)

    # Fallback: generic queries based on top skills
    top_skills = resume_data.skills[:2] or ["machine learning"]
    return [
        f"fundamentals and theory of {top_skills[0]}",
        "model evaluation metrics bias variance tradeoff",
        "optimization algorithms gradient descent convergence",
    ][:3]


def _chapter_position_to_difficulty(pos: Optional[float]) -> str:
    """Map chapter_position (0→1) to difficulty label."""
    if pos is None:
        return "Intermediate"
    if pos < 0.35:
        return "Fundamentals"
    elif pos < 0.65:
        return "Intermediate"
    else:
        return "Advanced"


async def retrieve_chunks(
    queries: List[str],
    db: AsyncSession,
    top_k: int = 5,
    difficulty_target: float = 0.5,
    alpha: float = 0.3,
) -> List[ChunkResult]:
    """
    Run cosine similarity search for each query against the chunks table,
    apply soft difficulty bias using chapter_position, deduplicate by chunk_id.

    Args:
        queries: List of retrieval query strings.
        db: Async DB session.
        top_k: Number of results per query before dedup.
        difficulty_target: Target difficulty 0.0–1.0 (from adaptive engine).
        alpha: Difficulty bias strength (0.3 = moderate bias toward target chapter position).

    Returns:
        Deduplicated list of ChunkResult, sorted by biased score descending.
    """
    if not queries:
        return []

    seen_chunk_ids: set[int] = set()
    all_results: List[ChunkResult] = []

    for query in queries:
        try:
            query_embedding = await _embed_query_async(query)
        except Exception as exc:
            logger.error("Embedding failed for query '%s': %s", query[:50], exc)
            continue

        # pgvector cosine distance query with chapter_position bias
        # Biased score = cosine_similarity * (1 - alpha * |chapter_position - difficulty_target|)
        # We search a larger pool (top_k * 3) and then apply the bias in Python
        sql = text("""
            SELECT
                c.id AS chunk_id,
                c.content,
                1 - (c.embedding <=> :query_vec) AS similarity,
                cs.book,
                cs.chapter,
                cs.section,
                cs.page,
                cs.chapter_position
            FROM chunks c
            JOIN chunk_sources cs ON cs.chunk_id = c.id
            ORDER BY c.embedding <=> :query_vec
            LIMIT :limit
        """)

        result = await db.execute(
            sql,
            {
                "query_vec": str(query_embedding),
                "limit": top_k * 3,
            },
        )
        rows = result.fetchall()

        for row in rows:
            if row.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(row.chunk_id)

            chapter_pos = row.chapter_position
            if chapter_pos is not None:
                bias_penalty = alpha * abs(chapter_pos - difficulty_target)
                biased_score = row.similarity * (1.0 - bias_penalty)
            else:
                biased_score = row.similarity

            all_results.append(
                ChunkResult(
                    chunk_id=row.chunk_id,
                    content=row.content,
                    similarity=biased_score,
                    book=row.book,
                    chapter=row.chapter,
                    section=row.section,
                    page=row.page,
                    chapter_position=chapter_pos,
                    difficulty=_chapter_position_to_difficulty(chapter_pos),
                )
            )

    # Sort by biased score, return top-k unique chunks
    all_results.sort(key=lambda r: r.similarity, reverse=True)
    final = all_results[: top_k * len(queries)]
    logger.info(
        "Retrieved %d unique chunks for %d queries (difficulty_target=%.2f)",
        len(final), len(queries), difficulty_target
    )
    return final


async def _embed_query_async(query: str) -> List[float]:
    """Run the CPU-bound embedding in a thread pool to avoid blocking the event loop."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, embed_query, query)
