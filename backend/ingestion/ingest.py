"""
Viva — Ingestion CLI Entry Point

Run this once before the demo to ingest all three textbooks into pgvector.

Usage:
    cd backend
    python -m ingestion.ingest

Or with explicit PDF directory:
    python -m ingestion.ingest --books-dir data/books

Expected PDF files (place here before running):
    data/books/mitchell_machine_learning.pdf
    data/books/bishop_prml.pdf
    data/books/burkov_100page_ml.pdf

The script is idempotent: re-running it on an unchanged PDF is a no-op (file
hash check). If a PDF changes, the book is re-processed and new chunks added.
"""
import argparse
import asyncio
import hashlib
import logging
import os
import sys
from pathlib import Path

# Ensure the backend/ directory is on the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("viva.ingest")

# Mapping: filename stem → book slug
KNOWN_BOOKS = {
    "MachineLearningTomMitchell": "mitchell",
    "Bishop-Pattern-Recognition-and-Machine-Learning-2006": "bishop",
    "2019BurkovTheHundred-pageMachineLearning": "burkov",
}


def derive_slug(pdf_path: Path) -> str:
    """Derive book slug from filename stem."""
    stem = pdf_path.stem
    if stem in KNOWN_BOOKS:
        return KNOWN_BOOKS[stem]
    # Fallback: use first word of stem, lowercase
    return stem.split("_")[0].lower()


def sha256_file(path: Path) -> str:
    """SHA-256 hash of PDF file bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def discover_book_pdfs(books_dir: str) -> list[Path]:
    """Find all known PDF files in the books directory."""
    dir_path = Path(books_dir)
    if not dir_path.exists():
        logger.error("Books directory not found: %s", dir_path)
        sys.exit(1)

    found: list[Path] = []
    for stem in KNOWN_BOOKS:
        pdf_path = dir_path / f"{stem}.pdf"
        if pdf_path.exists():
            found.append(pdf_path)
        else:
            logger.warning("PDF not found (will skip): %s", pdf_path)

    if not found:
        logger.error(
            "No known PDFs found in %s. Check KNOWN_BOOKS mapping.",
            dir_path,
        )
        sys.exit(1)

    return found


async def run_ingestion(books_dir: str) -> None:
    """Main ingestion orchestrator."""
    from app.database import AsyncSessionLocal
    from app.models import IngestedBook
    from ingestion.pdf_extractor import extract_text_from_pdf
    from ingestion.chunker import chunk_pages
    from ingestion.embedder import embed_and_store, sha256_file as _sha256_file
    from app.config import get_settings

    settings = get_settings()

    pdf_paths = discover_book_pdfs(books_dir)
    logger.info("Found %d PDF(s) to process: %s", len(pdf_paths), [p.name for p in pdf_paths])

    total_new = 0
    total_dup = 0

    async with AsyncSessionLocal() as db:
        for pdf_path in pdf_paths:
            book_slug = derive_slug(pdf_path)
            file_hash = _sha256_file(pdf_path)

            # Check idempotency
            result = await db.execute(
                select(IngestedBook).where(IngestedBook.book_slug == book_slug)
            )
            existing = result.scalar_one_or_none()

            if existing and existing.file_hash == file_hash:
                logger.info(
                    "%s: unchanged (hash match), skipping — %d chunks already stored",
                    book_slug, existing.new_chunks_stored or 0,
                )
                continue

            if existing:
                logger.info("%s: PDF changed (new hash), re-processing", book_slug)
            else:
                logger.info("%s: first-time ingestion starting", book_slug)

            # --- Extract ---
            logger.info("[%s] Extracting text from %s...", book_slug, pdf_path.name)
            try:
                pages = extract_text_from_pdf(str(pdf_path))
            except Exception as exc:
                logger.error("[%s] Text extraction failed: %s — STOPPING", book_slug, exc)
                logger.error(
                    "Per build instructions: stopping rather than substituting placeholder content."
                )
                sys.exit(1)

            logger.info("[%s] Extracted %d pages with text", book_slug, len(pages))

            # --- Chunk ---
            logger.info("[%s] Chunking pages (target=%d tokens, overlap=%d)...",
                       book_slug, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
            chunks = chunk_pages(
                pages=pages,
                book_name=book_slug,
                chunk_size=settings.chunk_size_tokens,
                chunk_overlap=settings.chunk_overlap_tokens,
            )
            logger.info("[%s] Produced %d chunks", book_slug, len(chunks))

            # --- Embed + Store ---
            logger.info("[%s] Embedding and storing chunks (dedup threshold=%.2f)...",
                       book_slug, settings.similarity_dedup_threshold)
            new_count, dup_count = await embed_and_store(chunks, db)
            logger.info("[%s] Done — %d new chunks, %d deduplicated/mapped", book_slug, new_count, dup_count)

            # --- Record ingestion ---
            if existing:
                existing.file_hash = file_hash
                existing.filename = pdf_path.name
                existing.total_pages = len(pages)
                existing.total_chunks_seen = len(chunks)
                existing.new_chunks_stored = new_count
                existing.duplicate_chunks_mapped = dup_count
                from sqlalchemy import func
                existing.ingested_at = func.now()
            else:
                record = IngestedBook(
                    book_slug=book_slug,
                    filename=pdf_path.name,
                    file_hash=file_hash,
                    total_pages=len(pages),
                    total_chunks_seen=len(chunks),
                    new_chunks_stored=new_count,
                    duplicate_chunks_mapped=dup_count,
                )
                db.add(record)

            await db.commit()

            total_new += new_count
            total_dup += dup_count

    logger.info(
        "=" * 60 + "\nIngestion complete:\n"
        "  Total new chunks stored:     %d\n"
        "  Total chunks deduplicated:   %d\n"
        "  Total chunks seen:           %d\n"
        "  Dedup ratio: %.1f%%\n" + "=" * 60,
        total_new, total_dup, total_new + total_dup,
        (total_dup / (total_new + total_dup) * 100) if (total_new + total_dup) > 0 else 0,
    )
    logger.info(
        "\n>>> CHECKPOINT 1: Now run spot-check queries to verify retrieval quality.\n"
        ">>> See README for test query commands.\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Viva ingestion pipeline")
    parser.add_argument(
        "--books-dir",
        default=os.environ.get("BOOKS_DIR", "data/books"),
        help="Directory containing the three textbook PDFs",
    )
    args = parser.parse_args()
    asyncio.run(run_ingestion(args.books_dir))


if __name__ == "__main__":
    main()
