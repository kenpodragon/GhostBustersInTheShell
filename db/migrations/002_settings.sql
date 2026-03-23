-- Settings table (single-row config, enforced by CHECK constraint)
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1) DEFAULT 1,
    ai_enabled BOOLEAN NOT NULL DEFAULT true,
    ai_provider VARCHAR(50) NOT NULL DEFAULT 'claude',
    preferences JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed default row
INSERT INTO settings (id, ai_enabled, ai_provider)
VALUES (1, true, 'claude')
ON CONFLICT (id) DO NOTHING;
