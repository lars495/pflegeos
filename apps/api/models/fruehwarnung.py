import json
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import Base


class FruehwarnFrage(Base):
    __tablename__ = "fruehwarn_fragen"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    schluessel = Column(String, nullable=False, unique=True)
    text = Column(String, nullable=False)
    aktiv = Column(Boolean, nullable=False, default=True)
    position = Column(Integer, nullable=False, default=0)


class FruehwarnMeldung(Base):
    __tablename__ = "fruehwarn_meldungen"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    resident_id = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False)
    auffaelligkeiten = Column(Text, default="[]")
    freitext = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    def auffaelligkeiten_liste(self) -> list[str]:
        try:
            daten = self.auffaelligkeiten or "[]"
            ergebnis = json.loads(daten)
            if not isinstance(ergebnis, list):
                return []
            return [str(x) for x in ergebnis]
        except (json.JSONDecodeError, TypeError):
            return []


STANDARDFRAGEN: list[tuple[str, str]] = [
    ("weniger_gegessen_getrunken", "Hat weniger gegessen oder getrunken"),
    ("wirkt_anders", "Wirkt anders als sonst"),
    ("muede_schwach", "Ist müder, schwächer oder schläfriger als sonst"),
    ("spricht_weniger", "Spricht oder reagiert weniger als sonst"),
    ("mehr_hilfe", "Braucht mehr Hilfe als sonst"),
    ("unruhig_schmerz", "Wirkt unruhig oder hat vermutlich Schmerzen"),
]


async def standardfragen_sicherstellen(session: AsyncSession) -> None:
    # alle vorhandenen Schlüssel abrufen
    result = await session.execute(select(FruehwarnFrage.schluessel))
    vorhandene_schluessel = set(result.scalars().all())

    neue_fragen = False
    for idx, (schluessel, text) in enumerate(STANDARDFRAGEN, start=1):
        if schluessel not in vorhandene_schluessel:
            frage = FruehwarnFrage(
                schluessel=schluessel,
                text=text,
                position=idx,
                aktiv=True,
            )
            session.add(frage)
            neue_fragen = True

    if neue_fragen:
        await session.commit()
