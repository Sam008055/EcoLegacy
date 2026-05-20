-- Clear TTS cache to force regeneration with smallest.ai
DELETE FROM audio_cache WHERE character_id IN ('osho', 'tesla', 'hitler');

-- Optional: Clear all cache
-- DELETE FROM audio_cache;