from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from app.config.settings import get_settings
from app.database.connection import close_pool, init_pool
from app.database.schema import apply_schema
from app.embeddings import warmup_embeddings
from app.mcp.tools import food_image as food_image_tools
from app.mcp.tools import recipes as recipe_tools

settings = get_settings()


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    # Apply schema.sql first so every table (including recipe_embeddings)
    # exists before any tool runs. apply_schema() will raise a clear error
    # if pgvector is not installed on the PostgreSQL server.
    await apply_schema(settings.database_url)
    await init_pool(settings.database_url)
    await warmup_embeddings()
    try:
        yield
    finally:
        await close_pool()


mcp = FastMCP(settings.mcp_server_name, lifespan=lifespan)

recipe_tools.register_tools(mcp)
food_image_tools.register_tools(mcp)
