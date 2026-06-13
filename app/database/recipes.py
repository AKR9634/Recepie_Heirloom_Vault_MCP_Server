import asyncpg

from app.database.connection import get_pool


def _record_to_dict(record: asyncpg.Record | None) -> dict | None:
    if record is None:
        return None
    return dict(record)


async def create_recipe(
    title: str,
    recipe_text: str,
    region: str | None = None,
    occasion: str | None = None,
) -> dict:
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO recipes (title, recipe_text, region, occasion)
            VALUES ($1, $2, $3, $4)
            RETURNING id, title, recipe_text, region, occasion, created_at
            """,
            title,
            recipe_text,
            region,
            occasion,
        )

    return _record_to_dict(row)


async def get_recipe(recipe_id: str) -> dict | None:
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, title, recipe_text, region, occasion, created_at
            FROM recipes
            WHERE id = $1
            """,
            recipe_id,
        )

    return _record_to_dict(row)


async def list_recipes(limit: int = 20) -> list[dict]:
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, recipe_text, region, occasion, created_at
            FROM recipes
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )

    return [dict(row) for row in rows]


async def delete_recipe(recipe_id: str) -> dict | None:
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            DELETE FROM recipes
            WHERE id = $1
            RETURNING id, title, recipe_text, region, occasion, created_at
            """,
            recipe_id,
        )

    return _record_to_dict(row)
