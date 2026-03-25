-- 005_rule_configs.sql
-- Rules configuration system: DB-backed config with snapshots

-- Rule configs: each section has a default row (from git) and a user row (active)
CREATE TABLE IF NOT EXISTS rule_configs (
    id SERIAL PRIMARY KEY,
    section TEXT NOT NULL,
    config_data JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    version TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Each section has exactly one default and one user row
CREATE UNIQUE INDEX IF NOT EXISTS idx_rule_configs_section_default
    ON rule_configs (section, is_default);

-- Config snapshots: user-saved named configurations
CREATE TABLE IF NOT EXISTS config_snapshots (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    snapshot_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add version tracking to settings
ALTER TABLE settings ADD COLUMN IF NOT EXISTS app_version TEXT DEFAULT '1.0.0';
ALTER TABLE settings ADD COLUMN IF NOT EXISTS rules_version TEXT DEFAULT '1.0.0';
ALTER TABLE settings ADD COLUMN IF NOT EXISTS rules_version_date TEXT DEFAULT '2026-03-25';
