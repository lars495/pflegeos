"""Freiwillige private Frage nach der Übergabe."""

from __future__ import annotations

import datetime as dt
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_session
from apps.api.models.uebergabe_reflexion import UebergabeReflexion
from apps.api.ui.common import templates

FRAGE = "Welche Information über eine Bewohnerin oder einen Bewohner hat dir heute gefehlt?"

router = APIRouter()


@router.get("/ui/uebergabe-frage", response_class=HTMLResponse)
async def ui_frage(request: Request):
    return templates.TemplateResponse(request, "uebergabe_frage.html", {
        "frage": FRAGE,
        "status": None,
        "antwort": "",
    })


@router.post("/ui/uebergabe-frage", response_class=HTMLResponse)
async def ui_frage_speichern(
    request: Request,
    author: str = Form(""),
    antwort: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    author = author.strip()
    antwort = antwort.strip()

    if author and antwort:
        reflexion = UebergabeReflexion(
            author=author,
            frage=FRAGE,
            antwort=antwort,
            geteilt=False,
        )
        session.add(reflexion)
        await session.commit()
        status = "gespeichert"
    elif not antwort:
        status = "uebersprungen"
    else:  # antwort vorhanden, aber kein Kürzel
        status = "kuerzel_fehlt"

    return templates.TemplateResponse(request, "uebergabe_frage.html", {
        "frage": FRAGE,
        "status": status,
        "antwort": antwort,
    })


@router.get("/ui/uebergabe-frage/meine", response_class=HTMLResponse)
async def ui_meine(
    request: Request,
    author: str = "",
    session: AsyncSession = Depends(get_session),
):
    author = author.strip()
    if author:
        result = await session.execute(
            select(UebergabeReflexion)
            .where(UebergabeReflexion.author == author)
            .order_by(UebergabeReflexion.created_at.desc())
            .limit(20)
        )
        eintraege = result.scalars().all()
    else:
        eintraege = []

    return templates.TemplateResponse(request, "uebergabe_frage_liste.html", {
        "modus": "meine",
        "author": author,
        "eintraege": eintraege,
        "punkte": [],
    })


@router.post("/ui/uebergabe-frage/{reflexion_id}/teilen")
async def ui_teilen(
    reflexion_id: str,
    author: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    eintrag = await session.get(UebergabeReflexion, reflexion_id)
    if eintrag is None:
        raise HTTPException(status_code=404)
    if author.strip() != eintrag.author:
        raise HTTPException(status_code=403)

    eintrag.geteilt = True
    eintrag.geteilt_at = dt.datetime.utcnow()
    await session.commit()

    return RedirectResponse(
        url=f"/ui/uebergabe-frage/meine?author={quote(eintrag.author, safe='')}",
        status_code=303,
    )


@router.post("/ui/uebergabe-frage/{reflexion_id}/zuruecknehmen")
async def ui_zuruecknehmen(
    reflexion_id: str,
    author: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    eintrag = await session.get(UebergabeReflexion, reflexion_id)
    if eintrag is None:
        raise HTTPException(status_code=404)
    if author.strip() != eintrag.author:
        raise HTTPException(status_code=403)

    eintrag.geteilt = False
    eintrag.geteilt_at = None
    await session.commit()

    return RedirectResponse(
        url=f"/ui/uebergabe-frage/meine?author={quote(eintrag.author, safe='')}",
        status_code=303,
    )


@router.get("/ui/uebergabe-frage/team", response_class=HTMLResponse)
async def ui_team(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(UebergabeReflexion)
        .where(UebergabeReflexion.geteilt == True)
        .order_by(UebergabeReflexion.id)
    )
    eintraege = result.scalars().all()
    punkte = [e.antwort for e in eintraege]

    return templates.TemplateResponse(request, "uebergabe_frage_liste.html", {
        "modus": "team",
        "author": "",
        "eintraege": [],
        "punkte": punkte,
    })
