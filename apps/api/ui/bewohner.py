"""Bewohner:innen: Liste, Aufnahme, Profil, Biografie, Wünsche, Hinweise.

Reihenfolge beachten: /ui/bewohner/neu muss VOR /ui/bewohner/{resident_id} stehen."""

from __future__ import annotations

import datetime as dt  # noqa: F401
import random  # noqa: F401

from fastapi import APIRouter, Depends, Form, HTTPException, Request  # noqa: F401
from fastapi.responses import HTMLResponse, RedirectResponse  # noqa: F401
from sqlalchemy import func, select  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.audit import log_action  # noqa: F401
from apps.api.db import get_session
from apps.api.models.resident import Resident
from apps.api.models.beobachtung import Beobachtung
from apps.api.models.hinweis import PersonHinweis
from apps.api.models.uebergabe_notiz import UebergabeNotiz
from apps.api.ui.common import templates

router = APIRouter()


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
    result = await session.execute(
        select(Beobachtung).where(Beobachtung.resident_id == resident_id)
        .order_by(Beobachtung.created_at.desc()).limit(5))
    beobachtungen = result.scalars().all()
    hinweise_result = await session.execute(
        select(PersonHinweis).where(PersonHinweis.resident_id == resident_id)
        .order_by(PersonHinweis.created_at))
    hinweise = hinweise_result.scalars().all()
    notizen_result = await session.execute(
        select(UebergabeNotiz)
        .where(UebergabeNotiz.resident_id == resident_id)
        .order_by(UebergabeNotiz.created_at.desc())
        .limit(10)
    )
    notizen = notizen_result.scalars().all()
    return templates.TemplateResponse(request, "bewohner_detail.html",
                                      {"person": person, "beobachtungen": beobachtungen,
                                       "hinweise": hinweise, "notizen": notizen})


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
