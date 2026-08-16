"""
Viva — PDF Text Extractor
Extracts text page-by-page using pdfplumber.
Returns a list of PageText namedtuples with page number and extracted text.
"""
import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    page_number: int
    text: str


def extract_text_from_pdf(pdf_path: str) -> List[PageText]:
    """
    Extract text from a PDF file, one PageText per page.

    Uses pdfplumber which handles multi-column academic textbook layouts
    better than pypdf by using spatial/coordinate-based extraction.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        List of PageText, skipping pages with no extractable text.

    Raises:
        FileNotFoundError: If the PDF path doesn't exist.
        ValueError: If no text could be extracted from any page.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages: List[PageText] = []
    empty_page_count = 0

    with pdfplumber.open(str(path)) as pdf:
        total_pages = len(pdf.pages)
        logger.info("Extracting text from %s (%d pages)", path.name, total_pages)

        for page in pdf.pages:
            page_num = page.page_number
            try:
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text and text.strip():
                    # Clean up common PDF artifacts
                    cleaned = _clean_page_text(text)
                    if cleaned.strip():
                        pages.append(PageText(page_number=page_num, text=cleaned))
                else:
                    empty_page_count += 1
                    logger.debug("Page %d: no extractable text (may be image/figure)", page_num)
            except Exception as exc:
                logger.warning("Failed to extract page %d: %s", page_num, exc)
                empty_page_count += 1

    if not pages:
        raise ValueError(
            f"No text extracted from {path.name}. "
            "The PDF may be scanned/image-based and requires OCR."
        )

    logger.info(
        "Extracted %d pages with text, %d empty/skipped from %s",
        len(pages), empty_page_count, path.name,
    )
    return pages


def _clean_page_text(text: str) -> str:
    """
    Remove common PDF extraction artifacts from page text.
    Preserves paragraph structure while removing noise.
    """
    # Remove form-feed characters
    text = text.replace("\f", "\n")
    # Collapse more than 2 consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove page number artifacts (lone numbers on a line)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Remove hyphenated line breaks (e.g. "opti-\nmization" → "optimization")
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Collapse excess whitespace on a single line
    text = re.sub(r"[ \t]{3,}", "  ", text)
    return text.strip()
