from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_session
from apps.api.models.resident import Resident
from apps.api.models.reflection import Reflection

router = APIRouter()

@router.get("/stats", tags=["meta"])
async def get_stats(
    session: AsyncSession = Depends(get_session)
) -> dict:
    residents_count = await session.scalar(
        select(func.count()).select_from(Resident)
    )
    reflections_count = await session.scalar(
        select(func.count()).select_from(Reflection)
    )
    return {
        "residents": residents_count,
        "reflections": reflections_count,
        "version": "0.1.0"
    }
