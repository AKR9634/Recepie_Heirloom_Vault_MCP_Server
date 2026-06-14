import uuid

from fastmcp import FastMCP

from app.database import recipes as recipe_db


def _validate_recipe_input(title: str, recipe_text: str) -> str | None:
    if not title.strip():
        return "Title cannot be empty"
    if not recipe_text.strip():
        return "Recipe text cannot be empty"
    return None


def _validate_recipe_id(recipe_id: str) -> str | None:
    if not recipe_id or not recipe_id.strip():
        return "Recipe ID cannot be empty"
    try:
        uuid.UUID(recipe_id)
    except ValueError:
        return "Invalid recipe ID format"
    return None


def _serialize_recipe(recipe: dict) -> dict:
    return {
        "id": str(recipe["id"]),
        "title": recipe["title"],
        "recipe_text": recipe["recipe_text"],
        "region": recipe["region"],
        "occasion": recipe["occasion"],
    }


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def add_recipe(
        title: str,
        recipe_text: str,
        region: str | None = None,
        occasion: str | None = None,
    ) -> dict:
        """Add a family recipe to the heirloom vault."""
        validation_error = _validate_recipe_input(title, recipe_text)
        if validation_error:
            return {"status": "error", "message": validation_error}

        try:
            recipe = await recipe_db.create_recipe(
                title=title.strip(),
                recipe_text=recipe_text.strip(),
                region=region,
                occasion=occasion,
            )
        except Exception as exc:
            return {"status": "error", "message": f"Failed to create recipe: {exc}"}

        return {
            "status": "success",
            "recipe_id": str(recipe["id"]),
            "message": "Recipe created successfully",
        }

    @mcp.tool
    async def get_recipe(recipe_id: str) -> dict:
        """Fetch a single recipe from the heirloom vault by its ID."""
        validation_error = _validate_recipe_id(recipe_id)
        if validation_error:
            return {"status": "error", "message": validation_error}

        try:
            recipe = await recipe_db.get_recipe(recipe_id)
        except Exception as exc:
            return {"status": "error", "message": f"Failed to fetch recipe: {exc}"}

        if recipe is None:
            return {"status": "error", "message": "Recipe not found"}

        return {
            "status": "success",
            "recipe": _serialize_recipe(recipe),
        }

    @mcp.tool
    async def list_recipes() -> dict:
        """List the most recent recipes from the heirloom vault."""
        try:
            recipes = await recipe_db.list_recipes()
        except Exception as exc:
            return {"status": "error", "message": f"Failed to list recipes: {exc}"}

        return {
            "status": "success",
            "count": len(recipes),
            "recipes": [_serialize_recipe(recipe) for recipe in recipes],
        }

    @mcp.tool
    async def search_recipes(query: str) -> dict:
        """Search recipes by title or recipe text using a case-insensitive substring match."""
        if not query or not query.strip():
            return {"status": "error", "message": "Search query cannot be empty"}

        try:
            recipes = await recipe_db.search_recipes(query.strip())
        except Exception as exc:
            return {"status": "error", "message": f"Failed to search recipes: {exc}"}

        return {
            "status": "success",
            "count": len(recipes),
            "recipes": [_serialize_recipe(recipe) for recipe in recipes],
        }
