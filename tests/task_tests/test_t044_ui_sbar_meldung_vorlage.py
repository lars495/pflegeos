import re

import pytest
from apps.api.main import app

if "/ui/bewohner/{resident_id}/sbar-meldung" not in {r.path for r in app.routes}:
    pytest.skip("T044 noch nicht umgesetzt", allow_module_level=True)
pytest.importorskip("apps.api.models.sbar_meldung")
pytest.importorskip("apps.api.models.fruehwarnung")
import datetime as dt  # noqa: E402

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select  # noqa: E402

VOLL = {
    "author": "km", "situation": "Fieber 38,5", "hintergrund": "Maria, Zimmer 12",
    "einschaetzung": "Möglicher Infekt", "empfehlung": "Bitte Visite", "fruehwarnung_id": "",
}


async def _person(client, name="Maria Bergmann", **kw):
    return (await client.post("/v1/residents", json={"name": name, **kw})).json()["id"]


def _textarea(html, name):
    m = re.search(rf'<textarea[^>]*name="{name}"[^>]*>(.*?)</textarea>', html, re.S)
    assert m, f"textarea {name} fehlt"
    return m.group(1)


async def _fruehwarnung(db_session, rid):
    """Legt ohne Kenntnis der Feldnamen eine Frühwarnung an; Textfelder bekommen Marker."""
    import apps.api.models.fruehwarnung as mod
    from apps.api.db import Base
    klassen = [o for o in vars(mod).values()
               if isinstance(o, type) and issubclass(o, Base) and o is not Base and o.__module__ == mod.__name__]
    assert klassen, "Keine Modellklasse in models/fruehwarnung.py"
    K = klassen[0]
    werte, marker = {}, []
    for c in K.__table__.columns:
        if c.name == "id":
            continue
        if c.name == "resident_id":
            werte[c.name] = rid
        elif isinstance(c.type, (String, Text)):
            werte[c.name] = f"M-{c.name}"
            marker.append(f"M-{c.name}")
        elif isinstance(c.type, DateTime):
            werte[c.name] = dt.datetime.utcnow()
        elif isinstance(c.type, Boolean):
            werte[c.name] = True
        elif isinstance(c.type, Integer):
            werte[c.name] = 1
    obj = K(**werte)
    db_session.add(obj)
    await db_session.commit()
    return obj.id, marker


async def _anzahl(db_session):
    from apps.api.models.sbar_meldung import SbarMeldung
    return len((await db_session.execute(select(SbarMeldung))).scalars().all())


async def test_leere_vorlage_mit_profildaten(client, db_session):
    rid = await _person(client, zimmer="12")
    r = await client.get(f"/ui/bewohner/{rid}/sbar-meldung")
    assert r.status_code == 200 and "<html" in r.text
    hg = _textarea(r.text, "hintergrund")
    assert "Maria Bergmann" in hg and "Zimmer 12" in hg
    assert f'action="/ui/bewohner/{rid}/sbar-meldung"' in r.text
    assert 'type="checkbox"' in r.text and 'name="bestaetigt"' in r.text
    assert await _anzahl(db_session) == 0  # GET speichert nie


async def test_vorlage_aus_fruehwarnung(client, db_session):
    rid = await _person(client, zimmer="12")
    fid, marker = await _fruehwarnung(db_session, rid)
    r = await client.get(f"/ui/bewohner/{rid}/sbar-meldung", params={"fruehwarnung_id": fid})
    assert r.status_code == 200
    situation = _textarea(r.text, "situation")
    assert any(m in situation for m in marker)
    assert f"fruehwarnung_id={fid}" in r.text  # Auswahl-Link vorhanden
    assert await _anzahl(db_session) == 0


async def test_einschaetzung_und_empfehlung_bleiben_leer(client, db_session):
    rid = await _person(client)
    fid, _ = await _fruehwarnung(db_session, rid)
    r = await client.get(f"/ui/bewohner/{rid}/sbar-meldung", params={"fruehwarnung_id": fid})
    assert _textarea(r.text, "einschaetzung").strip() == ""
    assert _textarea(r.text, "empfehlung").strip() == ""


async def test_fremde_fruehwarnung_wird_ignoriert(client, db_session):
    a = await _person(client, name="Person A")
    b = await _person(client, name="Person B")
    fid, marker = await _fruehwarnung(db_session, b)
    r = await client.get(f"/ui/bewohner/{a}/sbar-meldung", params={"fruehwarnung_id": fid})
    assert r.status_code == 200
    assert not any(m in r.text for m in marker)


async def test_unbekannte_fruehwarnung_kein_fehler(client):
    rid = await _person(client)
    r = await client.get(f"/ui/bewohner/{rid}/sbar-meldung", params={"fruehwarnung_id": "nope"})
    assert r.status_code == 200 and _textarea(r.text, "situation").strip() == ""


async def test_unbekannte_person_404(client):
    assert (await client.get("/ui/bewohner/nope/sbar-meldung")).status_code == 404
    assert (await client.post("/ui/bewohner/nope/sbar-meldung", data={**VOLL, "bestaetigt": "ja"})).status_code == 404


async def test_ohne_bestaetigung_nichts_gespeichert(client, db_session):
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/sbar-meldung", data=VOLL)
    assert r.status_code == 200
    assert "bestätige" in r.text
    assert "Fieber 38,5" in _textarea(r.text, "situation")  # Eingabe geht nicht verloren
    assert await _anzahl(db_session) == 0


async def test_bestaetigt_speichert_und_protokolliert(client, db_session):
    from apps.api.models.audit import AuditLog
    from apps.api.models.sbar_meldung import SbarMeldung
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/sbar-meldung", data={**VOLL, "bestaetigt": "ja"})
    assert r.status_code == 200 and "Gespeichert" in r.text
    m = (await db_session.execute(select(SbarMeldung))).scalars().one()
    assert m.resident_id == rid and m.author == "km"
    assert (m.situation, m.hintergrund, m.einschaetzung, m.empfehlung) == (
        "Fieber 38,5", "Maria, Zimmer 12", "Möglicher Infekt", "Bitte Visite")
    assert m.fruehwarnung_id is None
    assert f"/ui/sbar-meldung/{m.id}/druck" in r.text
    assert "sbar_meldung.gespeichert" in {e.action for e in (await db_session.execute(select(AuditLog))).scalars()}


async def test_bestaetigt_ohne_kuerzel_oder_situation_nichts(client, db_session):
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/sbar-meldung", data={**VOLL, "author": " ", "bestaetigt": "ja"})
    await client.post(f"/ui/bewohner/{rid}/sbar-meldung", data={**VOLL, "situation": "  ", "bestaetigt": "ja"})
    assert await _anzahl(db_session) == 0


async def test_eingaben_werden_escaped(client):
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/sbar-meldung",
                          data={**VOLL, "situation": "<script>alert(1)</script>"})
    assert "<script>alert" not in r.text
