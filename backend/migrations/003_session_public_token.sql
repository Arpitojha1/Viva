-- Add public_token to sessions
ALTER TABLE sessions ADD COLUMN public_token VARCHAR(36);

-- Backfill existing sessions
UPDATE sessions SET public_token = gen_random_uuid()::text WHERE public_token IS NULL;

-- Make it NOT NULL and UNIQUE
ALTER TABLE sessions ALTER COLUMN public_token SET NOT NULL;
ALTER TABLE sessions ADD CONSTRAINT sessions_public_token_key UNIQUE (public_token);
