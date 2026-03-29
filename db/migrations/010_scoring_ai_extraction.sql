-- 010_scoring_ai_extraction.sql
-- B.4/B.5/Phase C: Scoring integration, AI voice extraction, corpus management

BEGIN;

-- 1. Add purpose column to documents table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'purpose'
    ) THEN
        ALTER TABLE documents ADD COLUMN purpose VARCHAR(20) NOT NULL DEFAULT 'analysis';
        ALTER TABLE documents ADD CONSTRAINT chk_documents_purpose CHECK (purpose IN ('analysis', 'voice_corpus'));
    END IF;
END $$;

-- 2. Add content hash for dedup
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'content_hash'
    ) THEN
        ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64);
    END IF;
END $$;

-- 3. Indexes for documents
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_purpose ON documents(purpose);
CREATE INDEX IF NOT EXISTS idx_documents_profile_purpose ON documents(voice_profile_id, purpose);

-- 4. AI parse observations table
CREATE TABLE IF NOT EXISTS ai_parse_observations (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    qualitative_prompts JSONB NOT NULL DEFAULT '[]',
    metric_descriptions JSONB NOT NULL DEFAULT '[]',
    discovered_patterns JSONB NOT NULL DEFAULT '[]',
    raw_ai_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_observations_profile ON ai_parse_observations(profile_id);
CREATE INDEX IF NOT EXISTS idx_ai_observations_document ON ai_parse_observations(document_id);

-- 5. Consolidated AI analysis on voice_profiles
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'voice_profiles' AND column_name = 'consolidated_ai_analysis'
    ) THEN
        ALTER TABLE voice_profiles ADD COLUMN consolidated_ai_analysis JSONB;
    END IF;
END $$;

COMMIT;
