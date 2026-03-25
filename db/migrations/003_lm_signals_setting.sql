-- 003_lm_signals_setting.sql
-- Phase 3.8: Add lm_signals_enabled setting
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'settings' AND column_name = 'lm_signals_enabled'
    ) THEN
        ALTER TABLE settings ADD COLUMN lm_signals_enabled BOOLEAN DEFAULT FALSE;
    END IF;
END $$;
