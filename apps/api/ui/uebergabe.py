"""Übergabeansicht: die Person als roter Faden."""

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
    # Nur freigegebene Notizen — Entwürfe erscheinen nie in der Übergabe
    freigegeben = (await session.execute(
        select(UebergabeNotiz)
        .where(UebergabeNotiz.status == "freigegeben", UebergabeNotiz.freigegeben_at >= seit)
        .order_by(UebergabeNotiz.freigegeben_at.desc()))).scalars().all()
    notizen: dict[str, list] = {}
    for n in freigegeben:
        notizen.setdefault(n.resident_id, []).append(n)
    return templates.TemplateResponse(request, "uebergabe.html",
        {"personen": personen, "beobachtungen": je_person, "hinweise": hinweise,
         "notizen": notizen})
