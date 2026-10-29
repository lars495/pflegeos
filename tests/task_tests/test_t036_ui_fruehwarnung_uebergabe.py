import datetime as dt
from pathlib import Path

import pytest
from apps.api.main import app

_pfade = {r.path for r in app.routes}
_uebergabe_html = Path(__file__).resolve().parents[2] / "apps/api/templates/uebergabe.html"
if "/ui/bewohner/{resident_id}/fruehwarnung" not in _pfade or "/ui/uebergabe" not in _pfade:
    pytest.skip("T035 noch nicht umgesetzt", allow_module_level=True)
if not _uebergabe_html.exists() or "fruehwarnungen" not in _uebergabe_html.read_text(encoding="utf-8"):
    pytest.skip("T036 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402

from apps.api.models.fruehwarnung import FruehwarnFrage, FruehwarnMeldung  # noqa: E402

GEGESSEN = "Hat weniger gegessen oder getrunken"


async def _person(client, name="Maria Bergmann"):
    return (await client.post("/v1/residents", json={"name": name})).json()["id"]


async def test_meldung_erscheint_in_uebergabe(client, db_session):
    rid = await _person(client)
    await client.get(f"/ui/bewohner/{rid}/fruehwarnung")
    fid = (await db_session.execute(select(FruehwarnFrage).where(
        FruehwarnFrage.schluessel == "weniger_gegessen_getrunken"))).scalars().one().id
    await client.post(f"/ui/bewohner/{rid}/fruehwarnung",
                      data={"author": "hk", "ja": [fid], "freitext": "Trinkt kaum"})
    r = await client.get("/ui/uebergabe")
    assert r.status_code == 200
    assert "Frühwarnung" in r.text
    assert "Maria Bergmann" in r.text and GEGESSEN in r.text
    assert "Trinkt kaum" in r.text and "hk" in r.text
    assert "keine Diagnose" in r.text
    assert f'href="/ui/bewohner/{rid}"' in r.text


async def test_leerer_zustand_ist_freundlich(client):
    r = await client.get("/ui/uebergabe")
    assert r.status_code == 200
    assert "Keine Frühwarnungen" in r.text


async def test_alte_meldung_nicht_in_uebergabe(client, db_session):
    rid = await _person(client)
    jetzt = dt.datetime.utcnow()
    db_session.add(FruehwarnMeldung(resident_id=rid, author="hk", freitext="ALTE-MELDUNG",
                                    created_at=jetzt - dt.timedelta(days=3)))
    db_session.add(FruehwarnMeldung(resident_id=rid, author="hk", freitext="NEUE-MELDUNG",
                                    created_at=jetzt - dt.timedelta(hours=1)))
    await db_session.commit()
    t = (await client.get("/ui/uebergabe")).text
    assert "NEUE-MELDUNG" in t
    assert "ALTE-MELDUNG" not in t


async def test_reihenfolge_nur_nach_zeit_alle_stimmen_gleich(client, db_session):
    rid = await _person(client)
    jetzt = dt.datetime.utcnow()
    db_session.add(FruehwarnMeldung(resident_id=rid, author="pfk", freitext="ERSTE-MELDUNG",
                                    auffaelligkeiten='["a","b","c"]',
                                    created_at=jetzt - dt.timedelta(hours=3)))
    db_session.add(FruehwarnMeldung(resident_id=rid, author="hk", freitext="ZWEITE-MELDUNG",
                                    created_at=jetzt - dt.timedelta(hours=1)))
    await db_session.commit()
    t = (await client.get("/ui/uebergabe")).text
    assert "ERSTE-MELDUNG" in t and "ZWEITE-MELDUNG" in t
    assert t.index("ZWEITE-MELDUNG") < t.index("ERSTE-MELDUNG")  # neueste zuerst, unabhängig vom Autor


async def test_meldungen_mehrerer_personen(client, db_session):
    r1 = await _person(client, "Maria Bergmann")
    r2 = await _person(client, "Karl Sommer")
    for rid, text in ((r1, "TEXT-EINS"), (r2, "TEXT-ZWEI")):
        db_session.add(FruehwarnMeldung(resident_id=rid, author="hk", freitext=text))
    await db_session.commit()
    t = (await client.get("/ui/uebergabe")).text
    assert "Maria Bergmann" in t and "Karl Sommer" in t
    assert "TEXT-EINS" in t and "TEXT-ZWEI" in t


async def test_profil_verlinkt_die_karte(client):
    rid = await _person(client)
    t = (await client.get(f"/ui/bewohner/{rid}")).text
    assert f'href="/ui/bewohner/{rid}/fruehwarnung"' in t
