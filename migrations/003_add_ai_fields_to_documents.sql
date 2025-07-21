ALTER TABLE documents
    ADD COLUMN html_template TEXT,
    ADD COLUMN ai_generation_metadata JSONB,
    ADD COLUMN generated_sections JSONB;
-- AI fields: html_template (original HTML), ai_generation_metadata (generation metadata), generated_sections (per-section results) 