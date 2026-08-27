from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel  # noqa: F401

from apps.api.db import get_session
from apps.api.models.reflection import Reflection

router = APIRouter(prefix="/reflections", tags=["reflexionen"])

class ReflectionIn(BaseModel):
    author: str
    gut: str = ""
    schwierig: str = ""
    mitnehmen: str = ""

class ReflectionOut(BaseModel):
    id: str
    author: str
    gut: str
    schwierig: str
    mitnehmen: str
    nur_fuer_mich: bool

    class Config:
        from_attributes = True

@router.post("", response_model=ReflectionOut, status_code=201)
async def create_reflection(
    payload: ReflectionIn, session: AsyncSession = Depends(get_session)
) -> Reflection:
    obj = Reflection(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj

@router.get("", response_model=list[ReflectionOut])
async def list_reflections(
    author: str = Query(..., description="Pseudonym der Pflegekraft"),
    session: AsyncSession = Depends(get_session),
) -> list[Reflection]:
    result = await session.execute(
        select(Reflection).where(Reflection.author == author)
    )
    return result.scalars().all()
