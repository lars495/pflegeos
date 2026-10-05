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

import datetime as dt
from pathlib import Path

from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_session
from apps.api.models.resident import Resident
from apps.api.models.reflection import Reflection
from apps.api.models.beobachtung import Beobachtung
from apps.api.models.hinweis import PersonHinweis
from apps.api.audit import log_action

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

BEOBACHTUNG_KATEGORIEN = [
    "wirkt anders als sonst",
    "isst oder trinkt weniger",
    "braucht mehr Hilfe als sonst",
    "ist unruhiger oder ängstlicher",
    "schläft mehr oder ist schläfrig",
    "hat Schmerzen geäußert",
    "freut sich über etwas Besonderes",
]


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


@router.get("/ui/bewohner/{resident_id}/beobachtung", response_class=HTMLResponse)
async def ui_beobachtung_formular(resident_id: str, request: Request,
                                  session: AsyncSession = Depends(get_session)):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return templates.TemplateResponse(request, "beobachtung_neu.html",
        {"person": person, "kategorien": BEOBACHTUNG_KATEGORIEN})


@router.post("/ui/bewohner/{resident_id}/beobachtung")
async def ui_beobachtung_speichern(resident_id: str, request: Request,
        author: str = Form(""), kategorie: str = Form(""), notiz: str = Form(""),
        session: AsyncSession = Depends(get_session)):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    if not author.strip() or kategorie not in BEOBACHTUNG_KATEGORIEN:
        return templates.TemplateResponse(request, "beobachtung_neu.html",
            {"person": person, "kategorien": BEOBACHTUNG_KATEGORIEN,
             "fehler": "Bitte Kürzel und eine Beobachtung auswählen."})
    b = Beobachtung(resident_id=resident_id, author=author.strip(),
                    kategorie=kategorie, notiz=notiz.strip())
    session.add(b)
    await session.flush()
    await log_action(session, actor=author.strip(), action="beobachtung.created",
                     resource_type="resident", resource_id=resident_id)
    await session.commit()
    return RedirectResponse(f"/ui/bewohner/{resident_id}", status_code=303)


@router.get("/ui/bewohner/{resident_id}", response_class=HTMLResponse)
async def ui_bewohner_detail(
    resident_id: str, request: Request, session: AsyncSession = Depends(get_session)
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    result = await session.execute(
        select(Beobachtung).where(Beobachtung.resident_id == resident_id)
        .order_by(Beobachtung.created_at.desc()).limit(5))
    beobachtungen = result.scalars().all()
    hinweise_result = await session.execute(
        select(PersonHinweis).where(PersonHinweis.resident_id == resident_id)
        .order_by(PersonHinweis.created_at))
    hinweise = hinweise_result.scalars().all()
    return templates.TemplateResponse(request, "bewohner_detail.html",
                                      {"person": person, "beobachtungen": beobachtungen,
                                       "hinweise": hinweise})


@router.get("/ui/bewohner/{resident_id}/biografie", response_class=HTMLResponse)
async def ui_biografie_formular(
    resident_id: str, request: Request, session: AsyncSession = Depends(get_session)
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return templates.TemplateResponse(
        request, "_biografie.html", {"person": person, "bearbeiten": True}
    )


@router.post("/ui/bewohner/{resident_id}/biografie", response_class=HTMLResponse)
async def ui_biografie_speichern(
    resident_id: str, request: Request,
    biografie: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    person.biografie = biografie.strip()
    await session.commit()
    await session.refresh(person)
    return templates.TemplateResponse(
        request, "_biografie.html", {"person": person, "bearbeiten": False}
    )


@router.post("/ui/bewohner/{resident_id}/wuensche", response_class=HTMLResponse)
async def ui_wunsch_hinzufuegen(
    resident_id: str, request: Request,
    wunsch: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    if wunsch.strip():
        # neue Liste zuweisen, nicht .append() — sonst merkt SQLAlchemy
        # die Änderung am JSON-Feld nicht
        person.wuensche = [*person.wuensche, wunsch.strip()]
        await session.commit()
        await session.refresh(person)
    return templates.TemplateResponse(request, "_wuensche.html", {"person": person})


@router.post("/ui/bewohner/{resident_id}/hinweise", response_class=HTMLResponse)
async def ui_hinweis_hinzufuegen(
    resident_id: str, request: Request,
    text: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    if text.strip():
        hinweis = PersonHinweis(resident_id=resident_id, text=text.strip())
        session.add(hinweis)
        await session.commit()
    hinweise = (await session.execute(
        select(PersonHinweis).where(PersonHinweis.resident_id == resident_id)
        .order_by(PersonHinweis.created_at))).scalars().all()
    return templates.TemplateResponse(request, "_hinweise.html",
                                      {"person": person, "hinweise": hinweise})


@router.get("/ui/reflexion", response_class=HTMLResponse)
async def ui_reflexion_formular(request: Request):
    return templates.TemplateResponse(request, "reflexion.html", {})


@router.get("/ui/reflexion/meine", response_class=HTMLResponse)
async def ui_meine_reflexionen(
    request: Request, author: str = "", session: AsyncSession = Depends(get_session)
):
    eintraege = []
    if author.strip():
        result = await session.execute(
            select(Reflection)
            .where(Reflection.author == author.strip())
            .order_by(Reflection.created_at.desc())
        )
        eintraege = result.scalars().all()
    return templates.TemplateResponse(
        request, "reflexion_meine.html", {"eintraege": eintraege, "author": author}
    )


@router.post("/ui/reflexion")
async def ui_reflexion_speichern(
    request: Request,
    author: str = Form(""),
    gut: str = Form(""),
    schwierig: str = Form(""),
    mitnehmen: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    if not author.strip():
        return templates.TemplateResponse(
            request, "reflexion.html", {"fehler": "Bitte dein Kürzel eintragen."}
        )
    session.add(Reflection(
        author=author.strip(), gut=gut.strip(),
        schwierig=schwierig.strip(), mitnehmen=mitnehmen.strip(),
    ))
    await session.commit()
    return RedirectResponse(f"/ui/reflexion/meine?author={author.strip()}", status_code=303)


@router.get("/ui/uebergabe", response_class=HTMLResponse)
async def ui_uebergabe(request: Request, session: AsyncSession = Depends(get_session)):
    personen = (await session.execute(select(Resident).order_by(Resident.zimmer, Resident.name))).scalars().all()
    seit = dt.datetime.utcnow() - dt.timedelta(hours=24)
    beob = (await session.execute(
        select(Beobachtung).where(Beobachtung.created_at >= seit)
        .order_by(Beobachtung.created_at.desc()))).scalars().all()
    je_person: dict[str, list] = {}
    for b in beob:
        je_person.setdefault(b.resident_id, []).append(b)
    alle_hinweise = (await session.execute(
        select(PersonHinweis).order_by(PersonHinweis.created_at))).scalars().all()
    hinweise: dict[str, list] = {}
    for h in alle_hinweise:
        hinweise.setdefault(h.resident_id, []).append(h)
    return templates.TemplateResponse(request, "uebergabe.html",
        {"personen": personen, "beobachtungen": je_person, "hinweise": hinweise})
