"""PflegeOS API — minimal lauffähiges Skelett.

Phase 1 erweitert: Resident-Profile, Auth, Contribute-Endpoint.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 — registriert alle ORM-Modelle bei Base.metadata
from .db import Base, engine
from . import web
from .routes import contribute, health, residents, reflections, stats


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
app.include_router(residents.router, prefix="/v1", tags=["residents"])
app.include_router(reflections.router, prefix="/v1", tags=["reflexionen"])
app.include_router(stats.router, prefix="/v1", tags=["meta"])

# Pflege-Oberfläche (servergerendertes HTML unter /ui) + lokale Assets.
# HTMX liegt unter /static — bewusst kein CDN, es verlässt keine Anfrage den Server.
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.include_router(web.router, tags=["oberfläche"])


@app.get("/")
async def root() -> dict:
    return {
        "name": "PflegeOS",
        "version": app.version,
        "docs": "/docs",
        "principles": "https://github.com/lars495/pflegeos/blob/main/PRINCIPLES.md",
    }
