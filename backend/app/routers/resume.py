"""
Viva — Resume Router
POST /api/resume/upload — accept PDF, extract text, call Groq for structured data.
"""
import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.models import Resume
from app.schemas import ResumeUploadResponse
from app.services.resume_parser import parse_resume
from app.main import limiter

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["resume"])


@router.post(
    "/resume/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a candidate's resume PDF",
)
@limiter.limit(settings.rate_limit_resume)
async def upload_resume(
    request: Request,
    file: UploadFile = File(..., description="PDF resume, max 5MB"),
    db: AsyncSession = Depends(get_db),
) -> ResumeUploadResponse:
    """
    Upload a PDF resume, extract its text, and use Groq to extract structured
    entities (skills, technologies, domain exposure, experience level).

    Returns the resume ID and a flat list of extracted skill tokens for the
    frontend to display before the interview starts.
    """
    # --- Validation ---
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    content = await file.read(settings.max_resume_size_bytes + 1)
    if len(content) > settings.max_resume_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_resume_size_mb}MB limit.",
        )

    filename = file.filename or "resume.pdf"
    logger.info("Resume upload received: %s (%d bytes)", filename, len(content))

    # --- Extract text and compute hash BEFORE calling Groq ---
    from app.services.resume_parser import _extract_text_from_pdf, parse_resume
    import hashlib

    try:
        raw_text = _extract_text_from_pdf(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract text: {exc}",
        )

    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # --- Check cache ---
    cache_result = await db.execute(
        select(Resume).where(Resume.content_hash == content_hash).limit(1)
    )
    cached_resume = cache_result.scalar_one_or_none()

    if cached_resume is not None:
        logger.info(
            "Resume cache HIT: hash=%s, reusing resume id=%d (skip Groq call)",
            content_hash[:8], cached_resume.id,
        )
        from app.schemas import ExtractedResumeData
        resume_data = ExtractedResumeData(**(cached_resume.extracted_skills or {}))
        return ResumeUploadResponse(
            success=True,
            extractedSkills=resume_data.flat_skills_list(),
            resumeId=cached_resume.id,
        )

    # --- Cache MISS: call Groq ---
    logger.info("Resume cache MISS: hash=%s, calling Groq", content_hash[:8])
    try:
        resume_data, _, _ = await parse_resume(file_bytes=content, filename=filename, raw_text=raw_text)
    except Exception as exc:
        logger.error("Resume parsing failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse resume: {exc}",
        )

    # --- Persist ---
    resume_row = Resume(
        filename=filename,
        raw_text=raw_text,
        content_hash=content_hash,
        extracted_skills=resume_data.model_dump(),
        role="AI/ML Engineer",
        user_id=None,  # no user identity collected in this build
    )
    db.add(resume_row)
    await db.flush()  # get the generated ID without committing yet
    await db.refresh(resume_row)

    logger.info("Resume stored: id=%d, hash=%s, skills=%d", resume_row.id, content_hash[:8], len(resume_data.skills))

    return ResumeUploadResponse(
        success=True,
        extractedSkills=resume_data.flat_skills_list(),
        resumeId=resume_row.id,
    )
