import asyncpg

_pool: asyncpg.Pool | None = None


async def init_pool(database_url: str, *, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    global _pool

    if _pool is not None:
        return _pool

    _pool = await asyncpg.create_pool(database_url, min_size=min_size, max_size=max_size)
    return _pool


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_pool() first.")

    return _pool


async def close_pool() -> None:
    global _pool

    if _pool is None:
        return

    await _pool.close()
    _pool = None
