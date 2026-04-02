-- 011_add_element_routing.sql
-- Per-element format routing for voice style guide generation.
-- Strategies determined by Phase E format experiments.

CREATE TABLE IF NOT EXISTS element_routing (
    id SERIAL PRIMARY KEY,
    element_name VARCHAR(100) NOT NULL UNIQUE,
    strategy VARCHAR(50) NOT NULL CHECK (strategy IN (
        'json', 'json_enforced', 'english', 'hybrid', 'targeted_enforcement'
    )),
    best_score NUMERIC(6,4),
    detection_override VARCHAR(20) DEFAULT NULL CHECK (
        detection_override IS NULL OR detection_override IN ('detection_wins', 'voice_wins')
    ),
    enforcement_template TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add routing_version to settings table for version check pipeline
ALTER TABLE settings ADD COLUMN IF NOT EXISTS routing_version VARCHAR(20) DEFAULT '0.0.0';
