"""T001: Resident-ORM-Modell — die Spezifikation als Test."""
import datetime as dt

import pytest

resident_mod = pytest.importorskip(
    "apps.api.models.resident", reason="T001 noch nicht umgesetzt"
)


def test_klasse_und_tabelle():
    Resident = resident_mod.Resident
    assert Resident.__tablename__ == "residents"


def test_pflichtfelder_vorhanden():
    Resident = resident_mod.Resident
    cols = {c.name for c in Resident.__table__.columns}
    required = {
        "id", "name", "geburtsdatum", "zimmer", "einzugsdatum",
        "biografie", "beruf_frueher", "werte", "wuensche",
        "created_at", "updated_at",
    }
    fehlend = required - cols
    assert not fehlend, f"Fehlende Spalten: {fehlend}"


async def test_persistenz_und_defaults(db_session):
    Resident = resident_mod.Resident
    r = Resident(name="Max Mustermann", geburtsdatum=dt.date(1940, 5, 1))
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)

    assert r.id, "id muss automatisch gesetzt werden (UUID-String)"
    assert isinstance(r.id, str)
    assert r.name == "Max Mustermann"
    assert r.biografie == "", "biografie muss Default '' haben"
    assert r.werte == "", "werte muss Default '' haben"
    assert r.wuensche == [], "wuensche muss Default [] haben (JSON-Liste)"
    assert r.created_at is not None
