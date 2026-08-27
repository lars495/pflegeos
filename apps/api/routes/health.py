from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from apps.api.db import get_session

router = APIRouter()

HEALTHZ_CHECKS_DB = True

@router.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_session)) -> dict:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}

@router.get("/readyz")
async def readyz() -> dict:
    # Phase 1 expand: check db + redis
    return {"status": "ready"}
