-- 006_voice_profiles_redesign.sql
-- Phase 4.5.2: Voice Profiles Redesign

BEGIN;

-- 1. Add new columns to voice_profiles
ALTER TABLE voice_profiles
    ADD COLUMN IF NOT EXISTS profile_type VARCHAR(20) NOT NULL DEFAULT 'baseline',
    ADD COLUMN IF NOT EXISTS parse_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS stack_order INTEGER NOT NULL DEFAULT 0;

-- 2. Create profile_elements table
CREATE TABLE IF NOT EXISTS profile_elements (
    id SERIAL PRIMARY KEY,
    voice_profile_id INTEGER NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    element_type VARCHAR(20) NOT NULL DEFAULT 'directional',
    direction VARCHAR(10),
    weight FLOAT NOT NULL DEFAULT 0.5,
    target_value FLOAT,
    tags JSONB NOT NULL DEFAULT '[]',
    source VARCHAR(20) NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(voice_profile_id, name),
    CHECK (element_type IN ('directional', 'metric')),
    CHECK (direction IS NULL OR direction IN ('more', 'less')),
    CHECK (source IN ('parsed', 'manual')),
    CHECK (category IN ('lexical', 'character', 'syntactic', 'structural', 'content', 'idiosyncratic'))
);

CREATE INDEX IF NOT EXISTS idx_profile_elements_profile ON profile_elements(voice_profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_elements_category ON profile_elements(category);

-- 3. Create profile_prompts table
CREATE TABLE IF NOT EXISTS profile_prompts (
    id SERIAL PRIMARY KEY,
    voice_profile_id INTEGER NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profile_prompts_profile ON profile_prompts(voice_profile_id);

-- 4. Create profile_snapshots table
CREATE TABLE IF NOT EXISTS profile_snapshots (
    id SERIAL PRIMARY KEY,
    voice_profile_id INTEGER NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    snapshot_name VARCHAR(200) NOT NULL,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profile_snapshots_profile ON profile_snapshots(voice_profile_id);

-- 5. Add active profile columns to settings
ALTER TABLE settings
    ADD COLUMN IF NOT EXISTS active_baseline_id INTEGER REFERENCES voice_profiles(id),
    ADD COLUMN IF NOT EXISTS active_overlay_ids JSONB NOT NULL DEFAULT '[]';

-- 6. Set existing profile as default baseline
UPDATE voice_profiles SET profile_type = 'baseline', is_active = true WHERE id = 1;
UPDATE settings SET active_baseline_id = 1 WHERE id = 1;

COMMIT;
