CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    type VARCHAR(32) DEFAULT 'original',
    status VARCHAR(32) DEFAULT 'Uploaded',
    original_file_url VARCHAR(512) NOT NULL,
    ai_content TEXT,
    final_file_url VARCHAR(512),
    parsed_structure TEXT
); 