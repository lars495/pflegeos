"""Beobachtungen (Stop-and-Watch) und SBAR-Vorlage für den Arztanruf."""

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
from apps.api.models.sbar import SbarNotiz
from apps.api.ui.common import templates

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


@router.get("/ui/bewohner/{resident_id}/sbar", response_class=HTMLResponse)
async def ui_sbar_formular(resident_id: str, request: Request,
                           session: AsyncSession = Depends(get_session)):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")

    seit = dt.datetime.utcnow() - dt.timedelta(hours=24)
    beob_result = await session.execute(
        select(Beobachtung)
        .where(Beobachtung.resident_id == resident_id,
               Beobachtung.created_at >= seit)
        .order_by(Beobachtung.created_at.desc())
    )
    beobachtungen = beob_result.scalars().all()

    situation = "\n".join(
        b.kategorie + (f" — {b.notiz}" if b.notiz else "")
        for b in beobachtungen
    )
    hintergrund = (
        person.name
        + (f", Zimmer {person.zimmer}" if person.zimmer else "")
        + ". "
        + (person.biografie or "")[:200]
    )

    return templates.TemplateResponse(
        request, "sbar.html",
        {
            "person": person,
            "situation": situation,
            "hintergrund": hintergrund,
            "einschaetzung": "",
            "empfehlung": "",
        }
    )


@router.post("/ui/bewohner/{resident_id}/sbar")
async def ui_sbar_speichern(
    resident_id: str,
    request: Request,
    author: str = Form(""),
    situation: str = Form(""),
    hintergrund: str = Form(""),
    einschaetzung: str = Form(""),
    empfehlung: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")

    if not author.strip():
        return templates.TemplateResponse(
            request, "sbar.html",
            {
                "person": person,
                "situation": situation,
                "hintergrund": hintergrund,
                "einschaetzung": einschaetzung,
                "empfehlung": empfehlung,
                "fehler": "Bitte dein Kürzel eintragen.",
            }
        )

    notiz = SbarNotiz(
        resident_id=resident_id,
        author=author.strip(),
        situation=situation,
        hintergrund=hintergrund,
        einschaetzung=einschaetzung,
        empfehlung=empfehlung,
    )
    session.add(notiz)
    await session.flush()
    await log_action(
        session,
        actor=author.strip(),
        action="sbar.created",
        resource_type="resident",
        resource_id=resident_id,
    )
    await session.commit()
    return RedirectResponse(f"/ui/bewohner/{resident_id}", status_code=303)
