"""
Viva — Embedder
Embeds chunks in batches and upserts to the pgvector chunks + chunk_sources tables.
Implements the deduplication algorithm from Addendum 2:
  1. Exact content hash match → reuse existing chunk, add source mapping.
  2. Semantic near-duplicate (cosine sim ≥ threshold) → reuse existing chunk, add source mapping.
  3. Genuinely new → insert new chunk + source.
"""
import hashlib
import logging
import re
from typing import List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Chunk, ChunkSource
from app.utils.embeddings import embed_texts
from ingestion.chunker import Chunk as RawChunk

logger = logging.getLogger(__name__)
settings = get_settings()


def sha256_text(text_str: str) -> str:
    """SHA-256 hash of normalized text for exact-duplicate detection."""
    normalized = re.sub(r"\s+", " ", text_str).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str:
    """SHA-256 hash of a file (for ingested_books idempotency check)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def get_chunk_by_hash(db: AsyncSession, content_hash: str) -> Optional[Chunk]:
    """Look up a chunk by its exact content hash."""
    result = await db.execute(
        select(Chunk).where(Chunk.content_hash == content_hash)
    )
    return result.scalar_one_or_none()


async def find_nearest_chunk(
    db: AsyncSession,
    embedding: List[float],
    threshold: float,
) -> Optional[Chunk]:
    """
    Find the nearest existing chunk by cosine similarity.
    Returns the chunk only if similarity >= threshold.
    """
    sql = text("""
        SELECT id, content, content_hash,
               1 - (embedding <=> :query_vec) AS similarity
        FROM chunks
        ORDER BY embedding <=> :query_vec
        LIMIT 1
    """)
    result = await db.execute(sql, {"query_vec": str(embedding)})
    row = result.fetchone()
    if row and row.similarity >= threshold:
        # Return a lightweight Chunk-like object
        return await db.get(Chunk, row.id)
    return None


async def upsert_chunk_source(
    db: AsyncSession,
    chunk_id: int,
    raw_chunk: RawChunk,
) -> ChunkSource:
    """
    Insert a chunk_sources row for (chunk_id, book, page) if it doesn't exist.
    UNIQUE constraint on (chunk_id, book, page) handles idempotency.
    """
    m = raw_chunk.metadata
    existing = await db.execute(
        select(ChunkSource).where(
            ChunkSource.chunk_id == chunk_id,
            ChunkSource.book == m.book,
            ChunkSource.page == m.page,
        )
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row:
        return existing_row

    source = ChunkSource(
        chunk_id=chunk_id,
        book=m.book,
        chapter=m.chapter,
        section=m.section,
        page=m.page,
        chapter_position=m.chapter_position,
    )
    db.add(source)
    return source


async def embed_and_store(
    chunks: List[RawChunk],
    db: AsyncSession,
    batch_size: int = 32,
) -> Tuple[int, int]:
    """
    Embed chunks in batches, applying the 3-step deduplication algorithm.

    Returns:
        Tuple of (new_chunks_stored, duplicate_chunks_mapped).
    """
    new_count = 0
    dup_count = 0
    threshold = settings.similarity_dedup_threshold

    # Process in batches to control memory usage
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        batch_texts = [c.content for c in batch]

        # Embed entire batch at once (efficient — single model forward pass)
        try:
            embeddings = _embed_batch(batch_texts)
        except Exception as exc:
            logger.error("Embedding batch %d failed: %s", batch_start // batch_size, exc)
            continue

        for raw_chunk, embedding in zip(batch, embeddings):
            content_hash = sha256_text(raw_chunk.content)

            # --- Step 1: Exact content hash match ---
            existing_chunk = await get_chunk_by_hash(db, content_hash)
            if existing_chunk:
                await upsert_chunk_source(db, existing_chunk.id, raw_chunk)
                dup_count += 1
                continue

            # --- Step 2: Semantic near-duplicate ---
            await db.flush()  # make recently inserted chunks visible to search
            similar_chunk = await find_nearest_chunk(db, embedding, threshold)
            if similar_chunk:
                await upsert_chunk_source(db, similar_chunk.id, raw_chunk)
                dup_count += 1
                continue

            # --- Step 3: Genuinely new content ---
            new_chunk = Chunk(
                content=raw_chunk.content,
                content_hash=content_hash,
                embedding=embedding,
            )
            db.add(new_chunk)
            await db.flush()  # get the generated ID
            await db.refresh(new_chunk)
            await upsert_chunk_source(db, new_chunk.id, raw_chunk)
            new_count += 1

        # Commit after each batch so progress is persisted incrementally
        await db.commit()
        logger.info(
            "Batch %d/%d: %d new so far, %d deduped so far",
            batch_start // batch_size + 1,
            (len(chunks) + batch_size - 1) // batch_size,
            new_count, dup_count,
        )

    return new_count, dup_count


def _embed_batch(texts: List[str]) -> List[List[float]]:
    """Synchronous embedding call (runs in ingestion pipeline context, not async)."""
    return embed_texts(texts, is_query=False)
