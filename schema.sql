CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    recipe_text TEXT NOT NULL,
    region TEXT,
    occasion TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
