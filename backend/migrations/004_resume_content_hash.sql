-- backend/migrations/004_resume_content_hash.sql
ALTER TABLE resumes
  ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS resumes_content_hash_idx
  ON resumes(content_hash)
  WHERE content_hash IS NOT NULL;
