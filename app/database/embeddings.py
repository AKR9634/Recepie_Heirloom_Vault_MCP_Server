import asyncpg

from app.database.connection import get_pool


def _embedding_to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


async def store_embedding(recipe_id: str, embedding: list[float]) -> None:
    pool = get_pool()
    vector = _embedding_to_pgvector(embedding)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO recipe_embeddings (recipe_id, embedding)
            VALUES ($1, $2::vector)
            ON CONFLICT (recipe_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                created_at = NOW()
            """,
            recipe_id,
            vector,
        )


async def semantic_search_recipes(query_embedding: list[float], limit: int = 10) -> list[dict]:
    pool = get_pool()
    vector = _embedding_to_pgvector(query_embedding)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                r.id,
                r.title,
                r.recipe_text,
                r.region,
                r.occasion,
                r.created_at,
                e.embedding <=> $1::vector AS distance
            FROM recipes r
            INNER JOIN recipe_embeddings e ON r.id = e.recipe_id
            ORDER BY e.embedding <=> $1::vector
            LIMIT $2
            """,
            vector,
            limit,
        )

    return [dict(row) for row in rows]
