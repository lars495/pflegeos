"""Freiwillige private Frage nach der Übergabe."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
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
