-- 006b_voice_profiles_cleanup.sql
-- Run AFTER seed script has migrated voice_rules data

BEGIN;

ALTER TABLE voice_profiles DROP COLUMN IF EXISTS rules_json;
ALTER TABLE voice_profiles DROP COLUMN IF EXISTS sample_content;
DROP TABLE IF EXISTS voice_rules;

COMMIT;
