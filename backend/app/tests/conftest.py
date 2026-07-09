"""Test fixtures.

A session-scoped test database (`datails_test`) is created fresh, migrated to
head, and dropped afterwards. Application-role and owner-role sessions are
provided separately so LD-3 grant behavior is testable from both sides.

Environment overrides happen at import time, before any app module reads
settings.
"""

import asyncio
import os

# Point the app at the test database BEFORE app modules load settings.
TEST_DB_NAME = "datails_test"
_DB_HOST = os.environ.get("TEST_DB_HOST", "localhost")
_OWNER_DSN = f"postgresql+asyncpg://datails_owner:datails_owner_local@{_DB_HOST}:5432"
_APP_DSN = f"postgresql+asyncpg://datails_app:datails_app_local@{_DB_HOST}:5432"

os.environ["ENVIRONMENT"] = "local"
os.environ["DATABASE_URL"] = f"{_APP_DSN}/{TEST_DB_NAME}"
os.environ["DATABASE_MIGRATION_URL"] = f"{_OWNER_DSN}/{TEST_DB_NAME}"
os.environ["AUTH_DEV_MODE"] = "false"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.tests import auth_utils  # noqa: E402

os.environ["ENTRA_AUTHORITY"] = auth_utils.TEST_AUTHORITY
os.environ["ENTRA_AUDIENCE"] = auth_utils.TEST_AUDIENCE


def _alembic_config() -> Config:
    return Config("alembic.ini")


async def _recreate_database(name: str) -> None:
    import asyncpg

    conn = await asyncpg.connect(
        user="datails_owner",
        password="datails_owner_local",
        database="postgres",
        host=_DB_HOST,
        ssl=False,
    )
    await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    await conn.execute(f'CREATE DATABASE "{name}"')
    await conn.close()


async def _drop_database(name: str) -> None:
    import asyncpg

    conn = await asyncpg.connect(
        user="datails_owner",
        password="datails_owner_local",
        database="postgres",
        host=_DB_HOST,
        ssl=False,
    )
    await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    await conn.close()


@pytest.fixture(scope="session")
async def test_database():
    """Create the migrated test database once per test session.

    Alembic runs in a worker thread: its env.py calls asyncio.run(), which is
    illegal inside the already-running session loop.
    """
    await _recreate_database(TEST_DB_NAME)
    await asyncio.to_thread(command.upgrade, _alembic_config(), "head")
    yield TEST_DB_NAME
    await _drop_database(TEST_DB_NAME)


@pytest.fixture(scope="session")
async def app_engine(test_database):
    engine = create_async_engine(f"{_APP_DSN}/{TEST_DB_NAME}")
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def owner_engine(test_database):
    engine = create_async_engine(f"{_OWNER_DSN}/{TEST_DB_NAME}")
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_session(app_engine) -> AsyncSession:
    async with async_sessionmaker(app_engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
async def owner_session(owner_engine) -> AsyncSession:
    async with async_sessionmaker(owner_engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture(scope="session")
def app(test_database):  # noqa: ARG001 — depends on the migrated database
    """The FastAPI app, bound to the test database via the env overrides above."""
    from app.main import create_app

    return create_app()


@pytest.fixture
async def client(app) -> AsyncClient:
    """HTTP client against the app, with the JWKS cache seeded so real token
    validation runs without network access."""
    from app.core.auth import jwks_cache

    jwks_cache.seed(auth_utils.jwks_document())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture(scope="session", autouse=True)
async def _dispose_app_engine():
    yield
    from app.db.session import dispose_engine

    await dispose_engine()
