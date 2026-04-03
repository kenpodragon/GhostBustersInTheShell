-- 012_element_convergence.sql
-- Adds per-document element storage and convergence tracking for voice profiles.

-- Per-document element values (raw data for convergence analysis)
CREATE TABLE IF NOT EXISTS document_elements (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    element_name VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(profile_id, document_id, element_name)
);

CREATE INDEX IF NOT EXISTS idx_document_elements_profile ON document_elements(profile_id);
CREATE INDEX IF NOT EXISTS idx_document_elements_document ON document_elements(document_id);

-- Per-element convergence tracking (Welford's online algorithm state)
CREATE TABLE IF NOT EXISTS element_convergence (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    element_name VARCHAR(100) NOT NULL,
    running_mean FLOAT DEFAULT 0,
    running_count INTEGER DEFAULT 0,
    rolling_delta FLOAT DEFAULT 1.0,
    cv FLOAT DEFAULT 1.0,
    m2 FLOAT DEFAULT 0,
    consecutive_stable INTEGER DEFAULT 0,
    converged BOOLEAN DEFAULT FALSE,
    converged_at_words INTEGER DEFAULT NULL,
    UNIQUE(profile_id, element_name)
);

CREATE INDEX IF NOT EXISTS idx_element_convergence_profile ON element_convergence(profile_id);

-- Profile-level completeness columns
ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS total_words_parsed INTEGER DEFAULT 0;
ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS completeness_pct SMALLINT DEFAULT 0;
ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS completeness_tier VARCHAR(10) DEFAULT NULL;
