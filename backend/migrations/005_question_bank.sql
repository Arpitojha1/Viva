-- Migration 005: Add question_bank table for question reuse

CREATE TABLE IF NOT EXISTS question_bank (
    id SERIAL PRIMARY KEY,
    chunk_ids INTEGER[] NOT NULL,
    question_text TEXT NOT NULL,
    difficulty VARCHAR(20) NOT NULL CHECK (difficulty IN ('Fundamentals', 'Intermediate', 'Advanced')),
    times_served INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index to quickly find bank questions by difficulty that overlap with given chunk_ids
-- Note: A GIN index on chunk_ids would be ideal for overlap queries (&&), but 
-- for now a btree index on difficulty helps filter quickly, and the array overlap
-- can be evaluated on the remaining rows.
CREATE INDEX IF NOT EXISTS idx_question_bank_difficulty ON question_bank(difficulty);
