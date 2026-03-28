-- Migration 009: Add voice_tone category to profile_elements
-- Phase 4.5.3.2: Voice element expansion adds voice_tone category

ALTER TABLE profile_elements
    DROP CONSTRAINT profile_elements_category_check,
    ADD CONSTRAINT profile_elements_category_check
        CHECK (category IN ('lexical', 'character', 'syntactic', 'structural',
                            'content', 'idiosyncratic', 'voice_tone'));
