"""Slice 0 acceptance: the core-schema migration applies and rolls back
cleanly, including enum types (Postgres does not drop them with tables).

Uses a dedicated scratch database so the session-wide test database is
untouched.
"""

import asyncio
import os

import asyncpg
import pytest

from alembic import command
from alembic.config import Config
from app.tests.conftest import _DB_HOST, _OWNER_DSN

SCRATCH_DB = "datails_migration_roundtrip"


async def _owner_connect(database: str) -> asyncpg.Connection:
    return await asyncpg.connect(
        user="datails_owner",
        password="datails_owner_local",
        database=database,
        host=_DB_HOST,
        ssl=False,
    )


async def _recreate(name: str) -> None:
    conn = await _owner_connect("postgres")
    await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    await conn.execute(f'CREATE DATABASE "{name}"')
    await conn.close()


async def _drop(name: str) -> None:
    conn = await _owner_connect("postgres")
    await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    await conn.close()


async def _counts(name: str) -> tuple[int, int]:
    conn = await _owner_connect(name)
    tables = await conn.fetchval(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name != 'alembic_version'"
    )
    enums = await conn.fetchval("SELECT count(*) FROM pg_type WHERE typtype='e'")
    await conn.close()
    return tables, enums


@pytest.fixture
def scratch_db():
    original = os.environ["DATABASE_MIGRATION_URL"]
    os.environ["DATABASE_MIGRATION_URL"] = f"{_OWNER_DSN}/{SCRATCH_DB}"
    asyncio.run(_recreate(SCRATCH_DB))
    yield SCRATCH_DB
    os.environ["DATABASE_MIGRATION_URL"] = original
    asyncio.run(_drop(SCRATCH_DB))


def test_migration_up_down_up_leaves_no_residue(scratch_db) -> None:
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    tables_up, enums_up = asyncio.run(_counts(scratch_db))
    assert tables_up == 28, "expected the full Slice-0 core schema"
    assert enums_up == 25

    command.downgrade(config, "base")
    tables_down, enums_down = asyncio.run(_counts(scratch_db))
    assert tables_down == 0
    assert enums_down == 0, "downgrade must drop enum types too"

    command.upgrade(config, "head")
    tables_again, enums_again = asyncio.run(_counts(scratch_db))
    assert (tables_again, enums_again) == (tables_up, enums_up)
