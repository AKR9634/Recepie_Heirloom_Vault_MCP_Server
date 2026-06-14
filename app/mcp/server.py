from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from app.config.settings import get_settings
from app.database.connection import close_pool, init_pool
from app.mcp.tools import recipes as recipe_tools

settings = get_settings()


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    await init_pool(settings.database_url)
    try:
        yield
    finally:
        await close_pool()


mcp = FastMCP(settings.mcp_server_name, lifespan=lifespan)

recipe_tools.register_tools(mcp)
