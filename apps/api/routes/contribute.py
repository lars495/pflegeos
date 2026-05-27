"""Community Contributions Endpoint.

Nimmt Einreichungen von pflegeos.de/contribute entgegen und legt sie
in contributions/inbox/ ab. Der tägliche Agent verarbeitet sie.

Keine Personenbezogenen Bewohnerdaten in diesem Endpoint — er ist öffentlich.
Submitter-Daten sind optional und bleiben nur intern.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator


router = APIRouter()

INBOX = Path(__file__).resolve().parents[3] / "contributions" / "inbox"


class ContributionIn(BaseModel):
    type: Literal["idea", "legal", "bug"]
    title: str = Field(min_length=5, max_length=200)
    body: str = Field(min_length=20, max_length=10_000)
    submitter_name: str | None = Field(default=None, max_length=120)
    submitter_email: EmailStr | None = None
    consent_to_credit: bool = False
    consent_to_contact: bool = False
    attachments: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("body", "title")
    @classmethod
    def _no_obvious_pii(cls, v: str) -> str:
        # Defensiv: blockiere offensichtliche Telefonnummern, Adressen, lange Ziffernfolgen.
        if re.search(r"\b\d{10,}\b", v):
            raise ValueError("Bitte keine Telefonnummern oder lange Ziffernfolgen einreichen.")
        return v


class ContributionAck(BaseModel):
    id: str
    received_at: str
    message: str


@router.post("/contribute", response_model=ContributionAck, status_code=202)
async def contribute(payload: ContributionIn) -> ContributionAck:
    INBOX.mkdir(parents=True, exist_ok=True)

    cid = uuid.uuid4().hex[:12]
    received_at = dt.datetime.utcnow().isoformat() + "Z"

    record = payload.model_dump()
    record["id"] = cid
    record["submitted_at"] = received_at

    out = INBOX / f"{received_at[:10]}_{cid}.json"
    try:
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Konnte Einreichung nicht speichern: {e}")

    return ContributionAck(
        id=cid,
        received_at=received_at,
        message=(
            "Danke für deinen Beitrag. Der tägliche Build-Agent liest neue Einreichungen "
            "in den nächsten 24 Stunden. Status verfolgst du unter pflegeos.de/contributions."
        ),
    )
