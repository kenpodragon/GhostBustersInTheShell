-- Extension analysis history for report handoff
CREATE TABLE IF NOT EXISTS extension_analysis_history (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    result JSONB NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'manual',
    page_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ext_analysis_history_created ON extension_analysis_history(created_at);

-- Retention settings
ALTER TABLE settings ADD COLUMN IF NOT EXISTS analysis_history_max_count INTEGER DEFAULT 50;
ALTER TABLE settings ADD COLUMN IF NOT EXISTS analysis_history_ttl_hours INTEGER DEFAULT 24;
