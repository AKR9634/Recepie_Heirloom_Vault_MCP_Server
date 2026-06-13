import asyncio
from pathlib import Path

from app.config.settings import get_settings
from app.database.connection import close_pool, get_pool, init_pool
from app.database import recipes


async def apply_schema() -> None:
    schema_path = Path(__file__).resolve().parent.parent / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")

    async with get_pool().acquire() as conn:
        await conn.execute(sql)


async def main() -> None:
    settings = get_settings()
    await init_pool(settings.database_url)
    await apply_schema()

    created = await recipes.create_recipe(
        title="Grandma's Apple Pie",
        recipe_text="Peel apples. Mix with sugar and cinnamon. Bake at 375F for 45 minutes.",
        region="Midwest",
        occasion="Thanksgiving",
    )
    print("Created recipe:")
    print(created)

    recipe_id = str(created["id"])

    fetched = await recipes.get_recipe(recipe_id)
    print("\nFetched recipe:")
    print(fetched)

    all_recipes = await recipes.list_recipes()
    print(f"\nListed {len(all_recipes)} recipe(s):")
    for recipe in all_recipes:
        print(f"  - {recipe['title']} ({recipe['id']})")

    deleted = await recipes.delete_recipe(recipe_id)
    print("\nDeleted recipe:")
    print(deleted)

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
