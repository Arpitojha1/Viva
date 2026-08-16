-- Fix questions.difficulty CHECK constraint vocabulary
ALTER TABLE questions DROP CONSTRAINT IF EXISTS questions_difficulty_check;
ALTER TABLE questions ADD CONSTRAINT questions_difficulty_check
    CHECK (difficulty IN ('Fundamentals', 'Intermediate', 'Advanced'));

-- Add numeric_score to answers
ALTER TABLE answers ADD COLUMN IF NOT EXISTS numeric_score INTEGER;
