"""PflegeOS API — minimal lauffähiges Skelett.

Phase 1 erweitert: Resident-Profile, Auth, Contribute-Endpoint.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401 — registriert alle ORM-Modelle bei Base.metadata
from .db import Base, engine
from .routes import contribute, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tabellen anlegen (noch kein Alembic — siehe db.py).
    # In Tests übernimmt das die conftest-Fixture mit eigener Engine.
    if os.environ.get("ENV") != "test":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="PflegeOS API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — restriktiv per Default. Domains werden in Produktion via ENV gesetzt.
allowed = [d.strip() for d in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if d.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed or ["https://pflegeos.de", "https://care.pflegeos.de"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["meta"])
app.include_router(contribute.router, prefix="/v1", tags=["community"])
# Neue Router hier registrieren (Muster: app.include_router(x.router, prefix="/v1", tags=[...]))


@app.get("/")
async def root() -> dict:
    return {
        "name": "PflegeOS",
        "version": app.version,
        "docs": "/docs",
        "principles": "https://github.com/lars495/pflegeos/blob/main/PRINCIPLES.md",
    }
