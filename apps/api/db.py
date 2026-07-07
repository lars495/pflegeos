"""Zentrale Datenbank-Schicht.

- Produktion: PostgreSQL via asyncpg (DATABASE_URL aus Compose)
- Entwicklung/Tests: SQLite via aiosqlite (kein laufender Stack nötig)

Migrations: bewusst noch KEIN Alembic — Tabellen entstehen beim App-Start
über Base.metadata.create_all (siehe main.py lifespan). Alembic kommt,
sobald produktive Daten existieren, die Migrationen brauchen.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Basisklasse aller ORM-Modelle. Neue Modelle in apps/api/models/ ablegen —
    sie werden automatisch registriert (siehe models/__init__.py)."""


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./pflegeos_dev.db")
    # Compose liefert postgresql:// — der Async-Treiber braucht +asyncpg
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_database_url())
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-Dependency: eine DB-Session pro Request."""
    async with SessionLocal() as session:
        yield session
