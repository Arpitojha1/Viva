"""
Unit tests for the text chunker.
Tests chunk sizes, overlap, and metadata assignment.
Run: pytest tests/test_chunker.py -v
"""
import pytest
from ingestion.chunker import chunk_pages, count_tokens, Chunk
from ingestion.pdf_extractor import PageText


def make_pages(texts: list[str]) -> list[PageText]:
    return [PageText(page_number=i + 1, text=t) for i, t in enumerate(texts)]


def test_short_text_produces_single_chunk():
    """Text under chunk_size should produce exactly one chunk."""
    pages = make_pages(["This is a short text about machine learning."])
    chunks = chunk_pages(pages, book_name="test", chunk_size=600, chunk_overlap=80)
    assert len(chunks) == 1
    assert chunks[0].metadata.book == "test"
    assert chunks[0].metadata.page == 1


def test_long_text_produces_multiple_chunks():
    """Text significantly over chunk_size should produce multiple chunks."""
    # Create a long text (~1500 tokens)
    paragraph = "Machine learning is a field of AI. " * 40  # ~320 tokens
    long_text = "\n\n".join([paragraph] * 5)  # ~1600 tokens total
    pages = make_pages([long_text])
    chunks = chunk_pages(pages, book_name="mitchell", chunk_size=400, chunk_overlap=50)
    assert len(chunks) > 1


def test_chunk_size_within_tolerance():
    """Each chunk should be at most chunk_size + reasonable overhead."""
    paragraph = "The gradient descent algorithm updates weights by moving in the direction of steepest descent. " * 20
    long_text = "\n\n".join([paragraph] * 8)
    pages = make_pages([long_text])
    chunk_size = 300
    chunks = chunk_pages(pages, book_name="bishop", chunk_size=chunk_size, chunk_overlap=40)
    for chunk in chunks:
        token_count = count_tokens(chunk.content)
        # Allow 50% overhead due to overlap and splitting boundaries
        assert token_count <= chunk_size * 1.5, (
            f"Chunk too large: {token_count} tokens (limit: {chunk_size * 1.5})"
        )


def test_metadata_book_name_preserved():
    """book slug should be preserved in all chunk metadata."""
    pages = make_pages(["Some ML content here. " * 50])
    chunks = chunk_pages(pages, book_name="burkov", chunk_size=200, chunk_overlap=30)
    for chunk in chunks:
        assert chunk.metadata.book == "burkov"


def test_chapter_position_range():
    """chapter_position should be between 0.0 and 1.0."""
    texts = ["Page content " * 50] * 20
    pages = make_pages(texts)
    chunks = chunk_pages(pages, book_name="mitchell", chunk_size=300, chunk_overlap=40)
    for chunk in chunks:
        if chunk.metadata.chapter_position is not None:
            assert 0.0 <= chunk.metadata.chapter_position <= 1.0


def test_chapter_position_increases_over_book():
    """Later pages should have higher chapter_position than earlier pages."""
    texts = ["Page content about basics. " * 50] * 30
    pages = make_pages(texts)
    chunks = chunk_pages(pages, book_name="mitchell", chunk_size=300, chunk_overlap=40)
    # Early chunks should have lower position than late chunks
    if len(chunks) >= 4:
        early_pos = chunks[0].metadata.chapter_position or 0
        late_pos = chunks[-1].metadata.chapter_position or 0
        assert late_pos >= early_pos


def test_empty_pages_returns_empty():
    """No pages should return no chunks."""
    chunks = chunk_pages([], book_name="mitchell")
    assert chunks == []


def test_content_preserved():
    """Chunk content should contain meaningful text from the source."""
    text = "Supervised learning involves training a model on labeled data."
    pages = make_pages([text])
    chunks = chunk_pages(pages, book_name="mitchell", chunk_size=600, chunk_overlap=80)
    assert len(chunks) == 1
    assert "supervised" in chunks[0].content.lower()
