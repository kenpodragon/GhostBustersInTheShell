-- 004_document_sections_enhancements.sql
-- Phase 4: Add heading, classification, rewrite_comment, rewrite_iterations to document_sections

ALTER TABLE document_sections ADD COLUMN heading VARCHAR(500);
ALTER TABLE document_sections ADD COLUMN classification VARCHAR(50);
ALTER TABLE document_sections ADD COLUMN rewrite_comment TEXT;
ALTER TABLE document_sections ADD COLUMN rewrite_iterations INTEGER DEFAULT 0;
