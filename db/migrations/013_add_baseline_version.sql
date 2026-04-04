-- 013_add_baseline_version.sql
-- Add baseline voice profile version tracking to settings table.

ALTER TABLE settings ADD COLUMN IF NOT EXISTS baseline_version VARCHAR(20) DEFAULT NULL;
ALTER TABLE settings ADD COLUMN IF NOT EXISTS baseline_version_date TIMESTAMP DEFAULT NULL;
