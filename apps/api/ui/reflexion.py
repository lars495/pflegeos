"""Reflexion nach der Schicht — nur für die Pflegekraft selbst."""

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
from apps.api.models.reflection import Reflection
from apps.api.ui.common import templates

router = APIRouter()


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
