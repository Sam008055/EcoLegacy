-- Fix the cached_responses table to allow null audio_url
ALTER TABLE cached_responses ALTER COLUMN audio_url DROP NOT NULL;

-- Verify the change
\d cached_responses;