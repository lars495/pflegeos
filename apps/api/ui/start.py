"""Startseite."""

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
from apps.api.ui.common import templates

router = APIRouter()


@router.get("/ui", response_class=HTMLResponse)
async def ui_start(request: Request, session: AsyncSession = Depends(get_session)):
    """Startseite der Pflege-Oberfläche."""
    anzahl = await session.scalar(select(func.count()).select_from(Resident))
    return templates.TemplateResponse(
        request, "index.html", {"anzahl_bewohner": anzahl or 0}
    )
