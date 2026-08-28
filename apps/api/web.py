"""Pflege-Oberfläche — servergerendertes HTML mit Jinja2 + HTMX.

Bewusst kein JavaScript-Framework: Die Zielgruppe sind Pflegekräfte an
alten Bildschirmen und Tablets, nicht Entwickler. Servergerendertes HTML
ist barrierefrei by default, braucht keinen Build-Schritt und lädt auch
im WLAN-Funkloch eines Pflegeheims.

HTMX liegt lokal unter /static/ — es verlässt keine Anfrage den Server.

Aufbau für neue Seiten:
  1. Template unter apps/api/templates/<name>.html anlegen, das
     {% extends "base.html" %} nutzt
  2. Route hier ergänzen, mit `templates.TemplateResponse(request, "<name>.html", {...})`

Alle Routen hängen unter /ui — die JSON-API unter /v1 bleibt unberührt.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_session
from apps.api.models.resident import Resident

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


def initialen(name: str) -> str:
    """'Maria Lieselotte Bergmann' → 'MB' (für den Avatar-Kreis)."""
    teile = [t for t in name.split() if t]
    if not teile:
        return "?"
    if len(teile) == 1:
        return teile[0][:2].upper()
    return (teile[0][0] + teile[-1][0]).upper()


templates.env.filters["initialen"] = initialen


@router.get("/ui", response_class=HTMLResponse)
async def ui_start(request: Request, session: AsyncSession = Depends(get_session)):
    """Startseite der Pflege-Oberfläche."""
    anzahl = await session.scalar(select(func.count()).select_from(Resident))
    return templates.TemplateResponse(
        request, "index.html", {"anzahl_bewohner": anzahl or 0}
    )
