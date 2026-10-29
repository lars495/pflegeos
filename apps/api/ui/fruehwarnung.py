from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.audit import log_action
from apps.api.db import get_session
from apps.api.models.fruehwarnung import (
    FruehwarnFrage,
    FruehwarnMeldung,
    standardfragen_sicherstellen,
)
from apps.api.models.resident import Resident
from apps.api.ui.common import templates

router = APIRouter()


async def _seite(request, session, person, erfolg="", hinweistext=""):
    await standardfragen_sicherstellen(session)
    fragen = (await session.execute(
        select(FruehwarnFrage).order_by(FruehwarnFrage.position, FruehwarnFrage.id)
    )).scalars().all()
    return templates.TemplateResponse(
        request,
        "fruehwarnung_neu.html",
        {"person": person, "fragen": fragen, "erfolg": erfolg, "hinweistext": hinweistext},
    )


@router.get("/ui/bewohner/{resident_id}/fruehwarnung")
async def fruehwarnung_formular(
    resident_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return await _seite(request, session, person)


@router.post("/ui/bewohner/{resident_id}/fruehwarnung")
async def fruehwarnung_speichern(
    resident_id: str,
    request: Request,
    author: str = Form(""),
    ja: list[str] = Form(default=[]),
    freitext: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")

    if not author.strip():
        return await _seite(request, session, person, hinweistext="Bitte trag dein Kürzel ein.")

    await standardfragen_sicherstellen(session)

    aktive_fragen = (await session.execute(
        select(FruehwarnFrage)
        .where(FruehwarnFrage.aktiv == True)  # noqa: E712
        .order_by(FruehwarnFrage.position, FruehwarnFrage.id)
    )).scalars().all()

    ausgewaehlt = [f for f in aktive_fragen if f.id in ja]

    if not ausgewaehlt and not freitext.strip():
        return await _seite(
            request,
            session,
            person,
            hinweistext="Bitte kreuze etwas an oder schreib auf, was dir aufgefallen ist.",
        )

    meldung = FruehwarnMeldung(
        resident_id=resident_id,
        author=author.strip(),
        auffaelligkeiten=json.dumps([f.text for f in ausgewaehlt], ensure_ascii=False),
        freitext=freitext.strip(),
    )
    session.add(meldung)

    await log_action(
        session,
        actor=author.strip(),
        action="fruehwarnung.gemeldet",
        resource_type="resident",
        resource_id=resident_id,
    )
    await session.commit()

    return await _seite(
        request,
        session,
        person,
        erfolg="Danke! Deine Meldung ist gespeichert und erscheint in der nächsten Übergabe.",
    )


@router.post("/ui/bewohner/{resident_id}/fruehwarnung/fragen")
async def eigene_frage_hinzufuegen(
    resident_id: str,
    request: Request,
    text: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")

    await standardfragen_sicherstellen(session)

    if text.strip():
        max_pos_result = await session.execute(
            select(FruehwarnFrage.position).order_by(FruehwarnFrage.position.desc())
        )
        max_pos = max_pos_result.scalars().first()
        neue_position = (max_pos or 0) + 1

        neue_frage = FruehwarnFrage(
            schluessel="eigene_" + uuid.uuid4().hex[:8],
            text=text.strip(),
            aktiv=True,
            position=neue_position,
        )
        session.add(neue_frage)

        await log_action(
            session,
            actor="team",
            action="fruehwarnung.frage_geaendert",
            resource_type="resident",
            resource_id=resident_id,
        )
        await session.commit()

    return RedirectResponse(
        url=f"/ui/bewohner/{resident_id}/fruehwarnung", status_code=303
    )


@router.post("/ui/bewohner/{resident_id}/fruehwarnung/fragen/{frage_id}/umschalten")
async def frage_umschalten(
    resident_id: str,
    frage_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")

    frage = await session.get(FruehwarnFrage, frage_id)
    if frage is None:
        raise HTTPException(status_code=404, detail="Frage nicht gefunden")

    frage.aktiv = not frage.aktiv

    await log_action(
        session,
        actor="team",
        action="fruehwarnung.frage_geaendert",
        resource_type="resident",
        resource_id=resident_id,
    )
    await session.commit()

    return RedirectResponse(
        url=f"/ui/bewohner/{resident_id}/fruehwarnung", status_code=303
    )
