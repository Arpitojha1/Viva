-- ============================================================
-- Viva — Database Migration
-- Run this SQL in Supabase SQL Editor to set up all tables.
-- pgvector extension must be enabled first.
-- ============================================================

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Users (identity record, no auth in scope for this build)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    display_name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Resumes
-- ============================================================
CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),          -- nullable; set if upload flow collects identity
    filename VARCHAR(255) NOT NULL,
    raw_text TEXT NOT NULL,
    extracted_skills JSONB NOT NULL DEFAULT '{}',
    role VARCHAR(100) NOT NULL DEFAULT 'AI/ML Engineer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    resume_id INT NOT NULL REFERENCES resumes(id),
    user_id INT REFERENCES users(id),          -- denormalized for direct filter without join
    role VARCHAR(100) NOT NULL DEFAULT 'AI/ML Engineer',
    difficulty_target FLOAT NOT NULL DEFAULT 0.5,  -- 0.0=fundamentals, 1.0=advanced
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'abandoned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Chunks — one row per unique embedding (content-deduped across books)
-- ============================================================
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) UNIQUE NOT NULL,  -- sha256 of normalized text, exact-dup guard
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSW index for fast approximate cosine similarity search
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- Chunk Sources — one chunk can appear in multiple books/pages
-- ============================================================
CREATE TABLE IF NOT EXISTS chunk_sources (
    id SERIAL PRIMARY KEY,
    chunk_id INT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    book VARCHAR(100) NOT NULL,                -- "mitchell" | "bishop" | "burkov"
    chapter VARCHAR(200),
    section VARCHAR(300),
    page INT,
    chapter_position FLOAT,                    -- 0.0=start of book, 1.0=end (difficulty proxy)
    UNIQUE(chunk_id, book, page)
);

-- Index for fast chapter_position range queries (adaptive difficulty retrieval)
CREATE INDEX IF NOT EXISTS chunk_sources_book_position_idx
    ON chunk_sources(book, chapter_position);

-- ============================================================
-- Ingested Books — idempotency tracking for the ingestion pipeline
-- ============================================================
CREATE TABLE IF NOT EXISTS ingested_books (
    id SERIAL PRIMARY KEY,
    book_slug VARCHAR(100) UNIQUE NOT NULL,    -- "mitchell" | "bishop" | "burkov"
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,            -- sha256 of PDF bytes
    total_pages INT,
    total_chunks_seen INT,
    new_chunks_stored INT,
    duplicate_chunks_mapped INT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Questions
-- ============================================================
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    session_id INT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    chunk_ids INT[] NOT NULL,                  -- traceability: which chunks grounded this question
    question_text TEXT NOT NULL,
    difficulty VARCHAR(20) NOT NULL DEFAULT 'Intermediate'
        CHECK (difficulty IN ('Fundamentals', 'Intermediate', 'Advanced')),
    order_index INT NOT NULL,
    is_adaptive_followup BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS questions_session_idx ON questions(session_id, order_index);

-- ============================================================
-- Answers
-- ============================================================
CREATE TABLE IF NOT EXISTS answers (
    id SERIAL PRIMARY KEY,
    question_id INT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    quality_score VARCHAR(20)
        CHECK (quality_score IN ('weak', 'ok', 'strong')),
    score_reasoning TEXT,                      -- LLM's reasoning (useful for summary and debug)
    numeric_score INT,                         -- 0-100 mapped from quality: weak=35, ok=65, strong=90
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
