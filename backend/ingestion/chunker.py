"""
Viva — Text Chunker
Recursively splits extracted page text into overlapping chunks with metadata.
Target: ~600 tokens per chunk, ~80 token overlap, preserving book/chapter/page.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

import tiktoken

from ingestion.pdf_extractor import PageText

logger = logging.getLogger(__name__)

# GPT-2 tokenizer — good enough for token counting without needing a specific model.
# bge-small-en-v1.5 uses a different tokenizer but sizes are comparable for chunking purposes.
_TOKENIZER = tiktoken.get_encoding("gpt2")

# Chapter/section heading patterns for the three books
# These are heuristics — textbooks vary in formatting
_CHAPTER_PATTERNS = [
    re.compile(r"^(?:Chapter|CHAPTER)\s+(\d+)", re.MULTILINE),
    re.compile(r"^\d+\s+[A-Z][A-Za-z ]{4,50}$", re.MULTILINE),  # "1 Introduction"
]
_SECTION_PATTERNS = [
    re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s+[A-Z]", re.MULTILINE),  # "1.2 Section Title"
    re.compile(r"^[A-Z][A-Za-z ]{4,50}$", re.MULTILINE),
]


@dataclass
class ChunkMetadata:
    book: str
    chapter: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    chapter_position: Optional[float] = None  # 0.0→1.0 normalized position in book


@dataclass
class Chunk:
    content: str
    metadata: ChunkMetadata


def count_tokens(text: str) -> int:
    return len(_TOKENIZER.encode(text))


def chunk_pages(
    pages: List[PageText],
    book_name: str,
    chunk_size: int = 600,
    chunk_overlap: int = 80,
) -> List[Chunk]:
    """
    Split a book's extracted pages into overlapping chunks with metadata.

    Strategy:
    1. Detect chapter and section headings from page text using regex heuristics.
    2. Use recursive splitting: first by paragraph (double newline), then by sentence.
    3. Each chunk carries its source book, detected chapter, section, page, and
       normalized chapter_position (used as difficulty proxy).

    Args:
        pages: Ordered list of PageText from extract_text_from_pdf().
        book_name: Short book identifier ("mitchell", "bishop", "burkov").
        chunk_size: Target chunk size in tokens.
        chunk_overlap: Number of tokens to overlap between consecutive chunks.

    Returns:
        List of Chunk objects with content and metadata.
    """
    if not pages:
        return []

    total_pages = len(pages)
    chunks: List[Chunk] = []

    current_chapter: Optional[str] = None
    current_section: Optional[str] = None

    # Buffer for assembling text across pages before splitting into chunks
    text_buffer: List[str] = []
    buffer_pages: List[int] = []

    def flush_buffer(page_num: int) -> None:
        """Process accumulated text buffer into chunks."""
        if not text_buffer:
            return
        combined_text = "\n".join(text_buffer)
        page_chunks = _split_text_into_chunks(combined_text, chunk_size, chunk_overlap)
        for chunk_text in page_chunks:
            if chunk_text.strip():
                chapter_pos = page_num / total_pages if total_pages > 0 else 0.5
                chunks.append(
                    Chunk(
                        content=chunk_text.strip(),
                        metadata=ChunkMetadata(
                            book=book_name,
                            chapter=current_chapter,
                            section=current_section,
                            page=page_num,
                            chapter_position=round(chapter_pos, 4),
                        ),
                    )
                )

    for page in pages:
        # Detect chapter heading on this page
        for pattern in _CHAPTER_PATTERNS:
            m = pattern.search(page.text)
            if m:
                # Flush buffer before starting new chapter
                flush_buffer(page.page_number)
                text_buffer = []
                buffer_pages = []
                new_chapter = _extract_heading(page.text, m.start(), max_len=80)
                if new_chapter and new_chapter != current_chapter:
                    current_chapter = new_chapter
                    current_section = None
                    logger.debug("Chapter detected p.%d: %s", page.page_number, current_chapter)
                break

        # Detect section heading on this page
        for pattern in _SECTION_PATTERNS:
            m = pattern.search(page.text)
            if m:
                new_section = _extract_heading(page.text, m.start(), max_len=60)
                if new_section != current_section:
                    current_section = new_section
                break

        # Accumulate text; flush when buffer exceeds 3x chunk_size (prevents memory bloat)
        text_buffer.append(page.text)
        buffer_pages.append(page.page_number)

        if count_tokens("\n".join(text_buffer)) > chunk_size * 3:
            flush_buffer(page.page_number)
            # Keep last paragraph for overlap
            if text_buffer:
                last_para = text_buffer[-1].split("\n\n")[-1]
                text_buffer = [last_para]
                buffer_pages = [page.page_number]
            else:
                text_buffer = []
                buffer_pages = []

    # Final flush
    if text_buffer:
        flush_buffer(buffer_pages[-1] if buffer_pages else pages[-1].page_number)

    logger.info("Chunked %s: %d pages → %d chunks", book_name, total_pages, len(chunks))
    return chunks


def _split_text_into_chunks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    """
    Recursively split text into chunks of ~chunk_size tokens with overlap.

    Splits hierarchy: paragraph → sentence → word boundary.
    This mirrors LangChain's RecursiveCharacterTextSplitter logic but avoids
    the LangChain dependency and is simpler for our use case.
    """
    tokens = count_tokens(text)
    if tokens <= chunk_size:
        return [text]

    results: List[str] = []

    # Try splitting by double newline (paragraph)
    paragraphs = text.split("\n\n")
    if len(paragraphs) > 1:
        current: List[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = count_tokens(para)
            if current_tokens + para_tokens > chunk_size and current:
                results.append("\n\n".join(current))
                # Overlap: keep last paragraph(s) whose tokens ≤ chunk_overlap
                overlap_paras: List[str] = []
                overlap_tok = 0
                for p in reversed(current):
                    pt = count_tokens(p)
                    if overlap_tok + pt <= chunk_overlap:
                        overlap_paras.insert(0, p)
                        overlap_tok += pt
                    else:
                        break
                current = overlap_paras
                current_tokens = overlap_tok

            current.append(para)
            current_tokens += para_tokens

        if current:
            results.append("\n\n".join(current))

        return results

    # Fall back: split by sentence (period + space)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 1:
        current_sents: List[str] = []
        current_tokens = 0
        for sent in sentences:
            sent_tokens = count_tokens(sent)
            if current_tokens + sent_tokens > chunk_size and current_sents:
                results.append(" ".join(current_sents))
                current_sents = current_sents[-2:]  # keep 2 sentences for overlap
                current_tokens = sum(count_tokens(s) for s in current_sents)
            current_sents.append(sent)
            current_tokens += sent_tokens
        if current_sents:
            results.append(" ".join(current_sents))
        return results

    # Final fallback: hard split by token count
    words = text.split()
    current_words: List[str] = []
    current_tokens = 0
    for word in words:
        wt = count_tokens(word)
        if current_tokens + wt > chunk_size and current_words:
            results.append(" ".join(current_words))
            current_words = current_words[-10:]  # small word overlap
            current_tokens = sum(count_tokens(w) for w in current_words)
        current_words.append(word)
        current_tokens += wt
    if current_words:
        results.append(" ".join(current_words))
    return results


def _extract_heading(text: str, match_start: int, max_len: int = 80) -> Optional[str]:
    """Extract a heading string from text starting at match_start position."""
    snippet = text[match_start : match_start + max_len]
    # Take just the first line of the heading
    first_line = snippet.split("\n")[0].strip()
    return first_line if 3 < len(first_line) <= max_len else None
