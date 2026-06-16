import asyncio

from app.config.settings import get_settings
from app.database.connection import close_pool, init_pool
from app.mcp.server import mcp


async def startup() -> None:
    settings = get_settings()

    # print("DATABASE_URL =", settings.database_url)
    # print("MCP_SERVER_NAME =", settings.mcp_server_name)
    # print("HUGGINGFACE_EMBEDDING_MODEL =", settings.huggingface_embedding_model)
    # print("HUGGINGFACEHUB_API_TOKEN =", settings.huggingfacehub_api_token)

    print("Starting Recipe Heirloom Vault MCP Server...")
    
    await init_pool(settings.database_url)


def main() -> None:
    asyncio.run(startup())

    try:
        mcp.run()
    finally:
        asyncio.run(close_pool())


if __name__ == "__main__":
    main()
