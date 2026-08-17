"""
Viva — Pydantic Schemas
Request/response models for FastAPI endpoints.
Field names match the frontend API contract in frontend/src/lib/api.ts exactly.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Resume
# ============================================================

class ResumeUploadResponse(BaseModel):
    """Response from POST /api/resume/upload.
    Matches: api.uploadResume -> { success, extractedSkills }
    """
    success: bool
    extractedSkills: List[str]  # flat list: skills + technologies + domain_exposure combined
    # Internal ID stored server-side in session storage cookie / passed to createSession
    resumeId: int


class ExtractedResumeData(BaseModel):
    """Internal structured data extracted from a resume by Groq.
    Not returned directly to the frontend — used to populate resumeId's DB row
    and to drive retrieval query construction.
    """
    skills: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    experience_level: str = "mid"  # "junior" | "mid" | "senior"
    domain_exposure: List[str] = Field(default_factory=list)

    def flat_skills_list(self) -> List[str]:
        """Flatten all extracted entities into one deduplicated list for the frontend."""
        seen = set()
        result = []
        for item in self.skills + self.technologies + self.domain_exposure:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result


# ============================================================
# Session
# ============================================================

class SessionCreateRequest(BaseModel):
    """Request body for POST /api/session."""
    resumeId: int
    role: str = "AI/ML Engineer"


class SessionResponse(BaseModel):
    """Response from POST /api/session and GET /api/session/{id}.
    Matches: api.createSession -> { id, role, status }
    """
    id: str  # string per frontend contract (str(session.id))
    role: str
    status: str  # 'active' | 'completed'


class SessionDetailResponse(SessionResponse):
    """Extended session info for GET /api/session/{id}."""
    totalQuestions: int
    answeredCount: int
    createdAt: str


# ============================================================
# Question
# ============================================================

class SourceInfo(BaseModel):
    """Grounding source for a question.
    Matches: Question.source { book, chapter, page, similarity }
    Frontend shows a single source chip — we return the primary source
    (highest chapter_position proximity to current difficulty_target).
    """
    book: str
    chapter: str
    page: Optional[int] = None
    similarity: float  # cosine similarity score of the primary retrieval hit


class QuestionResponse(BaseModel):
    """Response from GET /api/interview/{session_id}/next-question.
    Matches: Question { id, text, difficulty, source }
    """
    id: str                           # str(question.id)
    text: str                         # question_text
    difficulty: str                   # 'Fundamentals' | 'Intermediate' | 'Advanced'
    source: SourceInfo                # primary grounding source
    isAdaptiveFollowup: Optional[bool] = False
    totalQuestions: Optional[int] = None
    currentIndex: Optional[int] = None


# ============================================================
# Answer
# ============================================================

class AnswerSubmitRequest(BaseModel):
    """Request body for POST /api/interview/{session_id}/answer.
    Matches: api.submitAnswer(sessionId, questionId, answer)
    """
    questionId: str
    answer: str


class AnswerSubmitResponse(BaseModel):
    """Response from POST /api/interview/{session_id}/answer.
    Matches: { score: number, nextDifficulty: 'Fundamentals'|'Intermediate'|'Advanced' }
    """
    score: int          # numeric 0-100: weak=35, ok=65, strong=90
    nextDifficulty: str  # 'Fundamentals' | 'Intermediate' | 'Advanced'
    hasNextQuestion: bool


# ============================================================
# Summary
# ============================================================

class ScoreDistribution(BaseModel):
    weak: int
    ok: int
    strong: int


class TranscriptItem(BaseModel):
    """One Q&A pair in the session transcript.
    Matches: Summary.transcript[i] { question, answer, score }
    """
    question: QuestionResponse
    answer: str
    score: int  # numeric 0-100

class PerformanceSeriesItem(BaseModel):
    orderIndex: int
    difficulty: str
    questionText: str
    answerText: str
    numericScore: int
    qualityScore: str
    scoreReasoning: str
    chunkIds: List[int]

class SummaryResponse(BaseModel):
    """Response from GET /api/session/{session_id}/summary.
    Matches: Summary { overallAssessment, strengths, gaps, scoreDistribution,
                       difficultyTrend, transcript }
    """
    overallAssessment: str
    strengths: List[str]
    gaps: List[str]
    scoreDistribution: ScoreDistribution
    difficultyTrend: List[int]  # sequence of 1/2/3 (Fundamentals/Intermediate/Advanced)
    transcript: List[TranscriptItem]
    performanceSeries: List[PerformanceSeriesItem]


# ============================================================
# Error
# ============================================================

class ErrorResponse(BaseModel):
    detail: str
