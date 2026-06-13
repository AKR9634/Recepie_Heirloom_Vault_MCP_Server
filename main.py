import asyncio

from app.config.settings import get_settings
from app.database.connection import close_pool, init_pool
from app.mcp.server import mcp


async def startup() -> None:
    settings = get_settings()
    await init_pool(settings.database_url)


def main() -> None:
    asyncio.run(startup())

    try:
        mcp.run()
    finally:
        asyncio.run(close_pool())


if __name__ == "__main__":
    main()
