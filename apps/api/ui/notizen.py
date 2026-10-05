"""Übergabe-Notizen: Entwurf und ausdrückliche Freigabe."""

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
from apps.api.models.uebergabe_notiz import UebergabeNotiz
from apps.api.ui.common import templates

router = APIRouter()


async def _notizen_fragment(request, session, person):
    notizen = (await session.execute(select(UebergabeNotiz)
        .where(UebergabeNotiz.resident_id == person.id)
        .order_by(UebergabeNotiz.created_at.desc()).limit(10))).scalars().all()
    return templates.TemplateResponse(request, "_notizen.html", {"person": person, "notizen": notizen})


@router.post("/ui/bewohner/{resident_id}/notizen", response_class=HTMLResponse)
async def ui_notiz_erstellen(
    resident_id: str,
    request: Request,
    author: str = Form(""),
    text: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    if author.strip() and text.strip():
        notiz = UebergabeNotiz(
            resident_id=resident_id,
            author=author.strip(),
            text=text.strip(),
            status="entwurf",
        )
        session.add(notiz)
        await session.commit()
    return await _notizen_fragment(request, session, person)


@router.post("/ui/notizen/{notiz_id}/freigeben", response_class=HTMLResponse)
async def ui_notiz_freigeben(
    notiz_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    notiz = await session.get(UebergabeNotiz, notiz_id)
    if notiz is None:
        raise HTTPException(status_code=404, detail="Notiz nicht gefunden")
    notiz.status = "freigegeben"
    notiz.freigegeben_at = dt.datetime.utcnow()
    await log_action(
        session,
        actor=notiz.author,
        action="notiz.freigegeben",
        resource_type="resident",
        resource_id=notiz.resident_id,
    )
    await session.commit()
    person = await session.get(Resident, notiz.resident_id)
    return await _notizen_fragment(request, session, person)
