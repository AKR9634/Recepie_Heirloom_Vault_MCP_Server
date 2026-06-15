-- Enable pgvector for semantic recipe search.
-- Requires the pgvector extension installed on your PostgreSQL server.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    recipe_text TEXT NOT NULL,
    region TEXT,
    occasion TEXT,
    story TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Idempotent migration for databases created before the story column existed.
ALTER TABLE recipes ADD COLUMN IF NOT EXISTS story TEXT;

CREATE TABLE IF NOT EXISTS recipe_embeddings (
    recipe_id UUID PRIMARY KEY REFERENCES recipes(id) ON DELETE CASCADE,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
