-- GhostBusters In The Shell - Initial Schema
-- Tables for document analysis, voice profiles, and detection results

-- Voice profiles for humanization guidance
CREATE TABLE IF NOT EXISTS voice_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    rules_json TEXT DEFAULT '{}',
    sample_content TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Documents uploaded for analysis
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500),
    file_type VARCHAR(20),  -- pdf, docx, txt
    original_text TEXT NOT NULL,
    overall_score FLOAT DEFAULT 0,
    analysis_json TEXT DEFAULT '{}',
    voice_profile_id INTEGER REFERENCES voice_profiles(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document sections for pagination and per-section rewriting
CREATE TABLE IF NOT EXISTS document_sections (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_order INTEGER NOT NULL,
    original_text TEXT NOT NULL,
    rewritten_text TEXT,
    ai_score FLOAT DEFAULT 0,
    patterns_json TEXT DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'pending',  -- pending, analyzed, rewritten, approved
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis history for tracking iterations
CREATE TABLE IF NOT EXISTS analysis_history (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES document_sections(id) ON DELETE CASCADE,
    input_text TEXT NOT NULL,
    output_text TEXT,
    score_before FLOAT,
    score_after FLOAT,
    method VARCHAR(50),  -- ai_provider, heuristic_fallback
    provider VARCHAR(50),  -- claude, gemini, python
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Detection heuristics configuration
CREATE TABLE IF NOT EXISTS detection_rules (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,  -- buzzword, structure, transition, hedge
    subcategory VARCHAR(100),
    rule_text VARCHAR(500) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    explanation TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Voice profile rules (parsed from voice guide)
CREATE TABLE IF NOT EXISTS voice_rules (
    id SERIAL PRIMARY KEY,
    voice_profile_id INTEGER NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    part INTEGER NOT NULL,
    part_title VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    rule_text TEXT NOT NULL,
    explanation TEXT,
    examples_bad TEXT,
    examples_good TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_score ON documents(overall_score);
CREATE INDEX IF NOT EXISTS idx_sections_document ON document_sections(document_id);
CREATE INDEX IF NOT EXISTS idx_sections_status ON document_sections(status);
CREATE INDEX IF NOT EXISTS idx_voice_rules_profile ON voice_rules(voice_profile_id);
CREATE INDEX IF NOT EXISTS idx_detection_rules_category ON detection_rules(category);
