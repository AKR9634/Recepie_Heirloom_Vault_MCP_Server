import uuid

from fastmcp import FastMCP

from app.database import embeddings as embedding_db
from app.database import recipes as recipe_db
from app.embeddings import generate_embedding


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


def _recipe_embedding_text(title: str, recipe_text: str) -> str:
    return f"{title}\n\n{recipe_text}"


async def create_recipe_with_embedding(
    title: str,
    recipe_text: str,
    region: str | None = None,
    occasion: str | None = None,
    *,
    fail_on_embedding_error: bool = False,
    success_message: str = "Recipe created successfully",
) -> dict:
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

    recipe_id = str(recipe["id"])
    embedding_text = _recipe_embedding_text(recipe["title"], recipe["recipe_text"])

    try:
        embedding = await generate_embedding(embedding_text)
        await embedding_db.store_embedding(recipe_id, embedding)
    except Exception as exc:
        if fail_on_embedding_error:
            return {"status": "error", "message": f"Failed to create recipe: {exc}"}
        return {
            "status": "success",
            "recipe_id": recipe_id,
            "title": recipe["title"],
            "message": success_message,
            "embedding_status": "failed",
            "embedding_error": str(exc),
        }

    return {
        "status": "success",
        "recipe_id": recipe_id,
        "title": recipe["title"],
        "message": success_message,
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
        return await create_recipe_with_embedding(
            title=title,
            recipe_text=recipe_text,
            region=region,
            occasion=occasion,
        )

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

    @mcp.tool
    async def semantic_search_recipes(query: str) -> dict:
        """Search recipes by meaning using embedding similarity."""
        if not query or not query.strip():
            return {"status": "error", "message": "Search query cannot be empty"}

        try:
            query_embedding = await generate_embedding(query.strip())
        except Exception as exc:
            return {"status": "error", "message": f"Failed to generate query embedding: {exc}"}

        try:
            recipes = await embedding_db.semantic_search_recipes(query_embedding)
        except Exception as exc:
            return {"status": "error", "message": f"Failed to search recipes: {exc}"}

        return {
            "status": "success",
            "count": len(recipes),
            "recipes": [_serialize_recipe(recipe) for recipe in recipes],
        }
