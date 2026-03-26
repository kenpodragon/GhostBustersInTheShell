-- Rename default voice profile to "Baseline"
UPDATE voice_profiles
SET name = 'Baseline'
WHERE name = 'Default - Anti-AI Voice Guide';
