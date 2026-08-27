from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_session
from apps.api.models.resident import Resident
from apps.api.schemas.resident import ResidentCreate, ResidentOut

router = APIRouter()

@router.post("/residents", response_model=ResidentOut, status_code=201)
async def create_resident(
    payload: ResidentCreate, session: AsyncSession = Depends(get_session)
) -> Resident:
    obj = Resident(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj

@router.get("/residents", response_model=list[ResidentOut])
async def list_residents(session: AsyncSession = Depends(get_session)) -> list[Resident]:
    result = await session.execute(select(Resident))
    return result.scalars().all()
