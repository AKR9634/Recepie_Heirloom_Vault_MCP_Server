from fastmcp import FastMCP

from app.config.settings import get_settings

settings = get_settings()

mcp = FastMCP(settings.mcp_server_name)
