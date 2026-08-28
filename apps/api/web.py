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

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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


@router.get("/ui/bewohner", response_class=HTMLResponse)
async def ui_bewohner_liste(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Resident).order_by(Resident.name))
    bewohner = result.scalars().all()
    return templates.TemplateResponse(request, "bewohner_liste.html", {"bewohner": bewohner})


@router.get("/ui/bewohner/neu", response_class=HTMLResponse)
async def ui_bewohner_neu_formular(request: Request):
    return templates.TemplateResponse(request, "bewohner_neu.html", {})


@router.post("/ui/bewohner/neu")
async def ui_bewohner_neu_speichern(
    request: Request,
    name: str = Form(""),
    zimmer: str = Form(""),
    biografie: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    if not name.strip():
        return templates.TemplateResponse(
            request, "bewohner_neu.html",
            {"fehler": "Bitte einen Namen eingeben."},
        )
    person = Resident(name=name.strip(), zimmer=zimmer.strip() or None,
                      biografie=biografie.strip())
    session.add(person)
    await session.commit()
    return RedirectResponse(f"/ui/bewohner/{person.id}", status_code=303)


@router.get("/ui/bewohner/{resident_id}", response_class=HTMLResponse)
async def ui_bewohner_detail(
    resident_id: str, request: Request, session: AsyncSession = Depends(get_session)
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return templates.TemplateResponse(request, "bewohner_detail.html", {"person": person})
