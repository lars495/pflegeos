"""Übergabe-Block einer Person: Biografie, Wünsche, Wohlbefinden zuerst.

Diese Seite schreibt nichts in die Datenbank. Sie zeigt nur, was im Profil
steht (oder was die Pflegekraft in einer gespeicherten Fassung bewusst
angepasst hat). Bearbeiten folgt in T042.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_session
from apps.api.models.beobachtung import Beobachtung
from apps.api.models.resident import Resident
from apps.api.models.uebergabe_notiz import UebergabeNotiz
from apps.api.models.uebergabe_profil import UebergabeProfil
from apps.api.ui.common import templates

router = APIRouter()

SCHLUESSEL = ("biografie", "wuensche", "wohlbefinden")


def _norm(text) -> str:
    """None → ''; '\\r\\n' → '\\n'; strip()."""
    if text is None:
        return ""
    return str(text).replace("\r\n", "\n").strip()


def _zeilen(text: str) -> list[str]:
    """Nicht-leere, gestrippte Zeilen."""
    return [z.strip() for z in text.splitlines() if z.strip()]


def _wohlbefinden_feld(person) -> str:
    """Name des Profil-Feldes für das Wohlbefinden, falls es eines gibt."""
    tabelle = getattr(person, "__table__", None)
    spalten = getattr(tabelle, "columns", [])
    for spalte in spalten:
        name = spalte.name
        if "wohlbefinden" in name or "stimmung" in name:
            return name
    return ""


async def vorbefuellung(session, person) -> dict[str, str]:
    """Texte aus dem Bewohnerprofil. Schlüssel: 'biografie', 'wuensche', 'wohlbefinden'."""
    roh_biografie = getattr(person, "biografie", None)
    if isinstance(roh_biografie, (list, tuple)):
        biografie = "\n".join(
            _norm(eintrag) for eintrag in roh_biografie if _norm(eintrag)
        )
    else:
        biografie = _norm(roh_biografie)

    roh_wuensche = getattr(person, "wuensche", None) or []
    if isinstance(roh_wuensche, str):
        roh_wuensche = [roh_wuensche]
    wuensche = "\n".join(_norm(wunsch) for wunsch in roh_wuensche if _norm(wunsch))

    feld = _wohlbefinden_feld(person)
    wohlbefinden = _norm(getattr(person, feld, None)) if feld else ""

    return {
        "biografie": biografie,
        "wuensche": wuensche,
        "wohlbefinden": wohlbefinden,
    }


async def _texte(session, person) -> dict[str, str]:
    """Wirksame Texte: gespeicherte Fassung, wenn gesetzt — sonst das Profil."""
    profil = (await session.execute(
        select(UebergabeProfil).where(UebergabeProfil.resident_id == person.id)
    )).scalars().first()
    vor = await vorbefuellung(session, person)
    texte: dict[str, str] = {}
    for schluessel in SCHLUESSEL:
        wert = getattr(profil, schluessel, None) if profil is not None else None
        texte[schluessel] = _norm(wert) if wert is not None else vor[schluessel]
    return texte


async def _seite(request, session, person, fehler=None, status_code=200):
    texte = await _texte(session, person)
    beobachtungen = (await session.execute(
        select(Beobachtung)
        .where(Beobachtung.resident_id == person.id)
        .order_by(Beobachtung.created_at.desc())
        .limit(10)
    )).scalars().all()
    notizen = (await session.execute(
        select(UebergabeNotiz)
        .where(
            UebergabeNotiz.resident_id == person.id,
            UebergabeNotiz.status == "freigegeben",
        )
        .order_by(UebergabeNotiz.created_at.desc())
        .limit(10)
    )).scalars().all()
    return templates.TemplateResponse(request, "uebergabe_profil.html", {
        "person": person,
        "fehler": fehler,
        "texte": texte,
        "biografie_zeilen": _zeilen(texte["biografie"]),
        "wuensche_zeilen": _zeilen(texte["wuensche"]),
        "wohlbefinden_zeilen": _zeilen(texte["wohlbefinden"]),
        "beobachtungen": beobachtungen,
        "notizen": notizen,
    }, status_code=status_code)


@router.get("/ui/bewohner/{resident_id}/uebergabe", response_class=HTMLResponse)
async def ui_uebergabe_profil(
    resident_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    person = await session.get(Resident, resident_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Bewohner:in nicht gefunden")
    return await _seite(request, session, person)
