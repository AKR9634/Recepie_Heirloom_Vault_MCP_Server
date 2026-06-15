"""Apply schema.sql against the configured database.

The schema is idempotent (`CREATE EXTENSION IF NOT EXISTS`,
`CREATE TABLE IF NOT EXISTS`) so it is safe to run on every server start.
If the `vector` extension is missing on the PostgreSQL server, the error
is re-raised with an actionable message pointing the user to the
pgvector install instructions.
"""

from __future__ import annotations

from pathlib import Path

import asyncpg

# Resolve the schema file relative to the project root (the directory that
# contains `app/` and `schema.sql`).
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"

_PGVECTOR_INSTALL_HINT = (
    "The PostgreSQL 'vector' extension (pgvector) is required but not "
    "installed on the database server. Install it and re-run:\n"
    "  - Debian/Ubuntu:  sudo apt install postgresql-16-pgvector\n"
    "  - macOS (Homebrew): brew install pgvector\n"
    "  - Windows:        use the pgvector build matching your Postgres, e.g.\n"
    "                    https://github.com/pgvector/pgvector/releases\n"
    "Then restart this server."
)


def _load_schema_sql() -> str:
    if not _SCHEMA_PATH.is_file():
        raise FileNotFoundError(
            f"schema.sql not found at expected location: {_SCHEMA_PATH}"
        )
    return _SCHEMA_PATH.read_text(encoding="utf-8")


async def apply_schema(database_url: str) -> None:
    """Connect to the database and apply schema.sql.

    Uses a short-lived single connection so this works even before the
    application connection pool is initialized.
    """
    sql = _load_schema_sql()

    try:
        conn = await asyncpg.connect(database_url)
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            f"Could not connect to the database to apply schema.sql: {exc}"
        ) from exc

    try:
        await conn.execute(sql)
    except asyncpg.UndefinedObjectError as exc:
        # The most common cause: the `vector` extension is not installed on
        # the PostgreSQL server. asyncpg raises UndefinedObjectError when
        # the extension lookup fails before CREATE EXTENSION runs.
        raise RuntimeError(_PGVECTOR_INSTALL_HINT) from exc
    except asyncpg.PostgresError as exc:
        # If the failure is specifically about the vector extension, give
        # the targeted hint; otherwise re-raise the original error.
        message = str(exc).lower()
        if "extension" in message and "vector" in message:
            raise RuntimeError(_PGVECTOR_INSTALL_HINT) from exc
        raise
    finally:
        await conn.close()
