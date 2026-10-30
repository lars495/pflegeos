import pytest

mod = pytest.importorskip("apps.api.models.uebergabe_reflexion")
from sqlalchemy import select  # noqa: E402


async def test_speichern_und_defaults(db_session):
    db_session.add(mod.UebergabeReflexion(author="km", frage="Welche Information hat gefehlt?", antwort="Der Zeitpunkt der letzten Mahlzeit"))
    await db_session.commit()
    row = (await db_session.execute(select(mod.UebergabeReflexion))).scalars().one()
    assert isinstance(row.id, str) and len(row.id) == 32
    assert row.geteilt is False
    assert row.geteilt_at is None
    assert row.created_at is not None
    assert row.author == "km"


def test_tabelle_und_spalten():
    assert mod.UebergabeReflexion.__tablename__ == "uebergabe_reflexionen"
    spalten = set(mod.UebergabeReflexion.__table__.columns.keys())
    assert spalten == {"id", "author", "frage", "antwort", "geteilt", "geteilt_at", "created_at"}


def test_keine_verknuepfung_zu_bewohnern():
    # Privatsphäre: Antworten dürfen nicht auf eine Person zurückführen.
    assert "resident_id" not in mod.UebergabeReflexion.__table__.columns.keys()


async def test_geteilt_kann_gesetzt_werden(db_session):
    import datetime as dt
    e = mod.UebergabeReflexion(author="km", frage="F", antwort="A", geteilt=True, geteilt_at=dt.datetime.utcnow())
    db_session.add(e)
    await db_session.commit()
    row = (await db_session.execute(select(mod.UebergabeReflexion))).scalars().one()
    assert row.geteilt is True and row.geteilt_at is not None
