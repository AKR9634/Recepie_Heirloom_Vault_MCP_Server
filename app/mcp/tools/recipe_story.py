from fastmcp import FastMCP

from app.database import recipes as recipe_db
from app.mcp.tools.recipes import _validate_recipe_id
from app.story import generate_recipe_story


async def run_generate_recipe_story(recipe_id: str) -> dict:
    validation_error = _validate_recipe_id(recipe_id)
    if validation_error:
        return {"status": "error", "message": validation_error}

    try:
        recipe = await recipe_db.get_recipe(recipe_id)
    except Exception:
        return {"status": "error", "message": "Unable to generate recipe story"}

    if recipe is None:
        return {"status": "error", "message": "Recipe not found"}

    recipe_id_str = str(recipe["id"])

    try:
        existing_story = await recipe_db.get_recipe_story(recipe_id_str)
    except Exception:
        return {"status": "error", "message": "Unable to generate recipe story"}

    if existing_story is not None:
        return {
            "status": "success",
            "recipe_id": recipe_id_str,
            "story": existing_story,
        }

    try:
        story = await generate_recipe_story(
            title=recipe["title"],
            recipe_text=recipe["recipe_text"],
            region=recipe.get("region"),
            occasion=recipe.get("occasion"),
        )
    except (ValueError, RuntimeError):
        return {"status": "error", "message": "Unable to generate recipe story"}

    try:
        await recipe_db.save_recipe_story(recipe_id_str, story)
    except Exception:
        return {"status": "error", "message": "Unable to generate recipe story"}

    return {
        "status": "success",
        "recipe_id": recipe_id_str,
        "story": story,
    }


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def generate_recipe_story(recipe_id: str) -> dict:
        """Generate a short cookbook-style narrative about a family recipe."""
        return await run_generate_recipe_story(recipe_id)
