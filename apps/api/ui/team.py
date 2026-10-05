"""Anonymes Team-Feedback zur Übergabe."""

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
from apps.api.models.team_feedback import TeamFeedback
from apps.api.ui.common import templates

router = APIRouter()


TEAM_MINDESTANZAHL = 3


@router.get("/ui/team", response_class=HTMLResponse)
async def ui_team(request: Request, session: AsyncSession = Depends(get_session)):
    alle = (await session.execute(select(TeamFeedback))).scalars().all()
    sichtbar = list(alle) if len(alle) >= TEAM_MINDESTANZAHL else []
    random.shuffle(sichtbar)
    return templates.TemplateResponse(request, "team.html", {
        "antworten": sichtbar, "anzahl": len(alle), "mindestanzahl": TEAM_MINDESTANZAHL})


@router.post("/ui/team")
async def ui_team_speichern(gefehlt: str = Form(""), unnoetig: str = Form(""), hilft: str = Form(""),
                            session: AsyncSession = Depends(get_session)):
    if gefehlt.strip() or unnoetig.strip() or hilft.strip():
        session.add(TeamFeedback(gefehlt=gefehlt.strip(), unnoetig=unnoetig.strip(), hilft=hilft.strip()))
        await session.commit()
    return RedirectResponse("/ui/team", status_code=303)
