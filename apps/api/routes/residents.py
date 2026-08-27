from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from apps.api.db import get_session
from apps.api.models.resident import Resident
from apps.api.schemas.resident import ResidentCreate, ResidentOut, ResidentUpdate
from apps.api.audit import log_action

router = APIRouter()

class WunschIn(BaseModel):
    wunsch: str

@router.post("/residents", response_model=ResidentOut, status_code=201)
async def create_resident(
    payload: ResidentCreate, session: AsyncSession = Depends(get_session)
) -> Resident:
    obj = Resident(**payload.model_dump())
    session.add(obj)
    await session.flush()
    await log_action(
        session,
        actor="system",
        action="resident.created",
        resource_type="resident",
        resource_id=obj.id,
    )
    await session.commit()
    await session.refresh(obj)
    return obj

@router.get("/residents", response_model=list[ResidentOut])
async def list_residents(session: AsyncSession = Depends(get_session)) -> list[Resident]:
    result = await session.execute(select(Resident))
    return result.scalars().all()

@router.get("/residents/{resident_id}", response_model=ResidentOut)
async def get_resident(
    resident_id: str, session: AsyncSession = Depends(get_session)
) -> Resident:
    obj = await session.get(Resident, resident_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    await session.refresh(obj)
    return obj

@router.patch("/residents/{resident_id}", response_model=ResidentOut)
async def update_resident(
    resident_id: str,
    payload: ResidentUpdate,
    session: AsyncSession = Depends(get_session),
) -> Resident:
    obj = await session.get(Resident, resident_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(obj, field, value)
    
    await log_action(
        session,
        actor="system",
        action="resident.updated",
        resource_type="resident",
        resource_id=resident_id,
    )
    await session.commit()
    await session.refresh(obj)
    return obj

@router.post("/residents/{resident_id}/wuensche", response_model=list[str])
async def add_wunsch(
    resident_id: str,
    payload: WunschIn,
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    obj = await session.get(Resident, resident_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    
    obj.wuensche = [*obj.wuensche, payload.wunsch]
    await session.commit()
    await session.refresh(obj)
    return obj.wuensche

@router.get("/residents/{resident_id}/wuensche", response_model=list[str])
async def get_wuensche(
    resident_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    obj = await session.get(Resident, resident_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    
    await session.refresh(obj)
    return obj.wuensche
