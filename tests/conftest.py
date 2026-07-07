"""Test-Fixtures für die gesamte Suite.

Tests laufen gegen SQLite (aiosqlite) — kein laufender Postgres nötig.
Jeder Test bekommt eine frische Datenbank (create_all/drop_all), die
FastAPI-Session-Dependency wird auf die Test-Engine umgebogen.

Verwendung in Tests:
    async def test_x(client):        # HTTP-Client gegen die App
        r = await client.post("/v1/residents", json={...})

    async def test_y(db_session):    # direkte DB-Session (ORM-Tests)
        db_session.add(obj); await db_session.commit()
"""

from __future__ import annotations

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ENV=test VOR dem App-Import setzen — verhindert create_all in lifespan
os.environ["ENV"] = "test"

from apps.api import models  # noqa: F401, E402 — Modelle registrieren
from apps.api.db import Base, get_session  # noqa: E402
from apps.api.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///./test_pflegeos.db"
)

# NullPool: jede Verbindung frisch — vermeidet Event-Loop-Konflikte zwischen Tests
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def _fresh_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(_fresh_db):
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(_fresh_db):
    async def _override_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
