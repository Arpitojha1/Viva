"""
Viva — SQLAlchemy ORM Models
One class per table. Uses pgvector's Vector type for the embedding column.
"""
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    resumes: Mapped[List["Resume"]] = relationship(back_populates="user")
    sessions: Mapped[List["Session"]] = relationship(back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_skills: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="AI/ML Engineer")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="resumes")
    sessions: Mapped[List["Session"]] = relationship(back_populates="resume")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="AI/ML Engineer")
    difficulty_target: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed', 'abandoned')", name="sessions_status_check"),
    )

    resume: Mapped["Resume"] = relationship(back_populates="sessions")
    user: Mapped[Optional["User"]] = relationship(back_populates="sessions")
    questions: Mapped[List["Question"]] = relationship(
        back_populates="session", order_by="Question.order_index"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(Vector(384), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sources: Mapped[List["ChunkSource"]] = relationship(back_populates="chunk")


class ChunkSource(Base):
    __tablename__ = "chunk_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
    )
    book: Mapped[str] = mapped_column(String(100), nullable=False)
    chapter: Mapped[Optional[str]] = mapped_column(String(200))
    section: Mapped[Optional[str]] = mapped_column(String(300))
    page: Mapped[Optional[int]] = mapped_column(Integer)
    chapter_position: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("chunk_id", "book", "page", name="chunk_sources_unique"),
    )

    chunk: Mapped["Chunk"] = relationship(back_populates="sources")


class IngestedBook(Base):
    __tablename__ = "ingested_books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer)
    total_chunks_seen: Mapped[Optional[int]] = mapped_column(Integer)
    new_chunks_stored: Mapped[Optional[int]] = mapped_column(Integer)
    duplicate_chunks_mapped: Mapped[Optional[int]] = mapped_column(Integer)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Intermediate"
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_adaptive_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('Fundamentals', 'Intermediate', 'Advanced')",
            name="questions_difficulty_check",
        ),
    )

    session: Mapped["Session"] = relationship(back_populates="questions")
    answer: Mapped[Optional["Answer"]] = relationship(
        back_populates="question", uselist=False
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[Optional[str]] = mapped_column(String(20))
    score_reasoning: Mapped[Optional[str]] = mapped_column(Text)
    numeric_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "quality_score IN ('weak', 'ok', 'strong')",
            name="answers_quality_score_check",
        ),
    )

    question: Mapped["Question"] = relationship(back_populates="answer")
