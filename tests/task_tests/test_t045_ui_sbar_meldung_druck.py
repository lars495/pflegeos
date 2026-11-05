import pytest
from apps.api.main import app

if "/ui/sbar-meldung/{meldung_id}/druck" not in {r.path for r in app.routes}:
    pytest.skip("T045 noch nicht umgesetzt", allow_module_level=True)
pytest.importorskip("apps.api.models.sbar_meldung")


async def _person(client, **kw):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann", **kw})).json()["id"]


async def _meldung(client, db_session, **kw):
    from apps.api.models.sbar_meldung import SbarMeldung
    rid = await _person(client, zimmer="12")
    m = SbarMeldung(
        resident_id=rid, author="km",
        situation=kw.get("situation", "Zeile eins\nZeile zwei"),
        hintergrund="Hintergrundtext", einschaetzung="Einschätzungstext", empfehlung="Empfehlungstext",
    )
    db_session.add(m)
    await db_session.commit()
    return rid, m.id


async def test_druckansicht_zeigt_alles(client, db_session):
    rid, mid = await _meldung(client, db_session)
    r = await client.get(f"/ui/sbar-meldung/{mid}/druck")
    assert r.status_code == 200 and "<html" in r.text
    for s in ("Maria Bergmann", "Zimmer 12", "km", "Hintergrundtext", "Einschätzungstext", "Empfehlungstext"):
        assert s in r.text
    for h in ("Situation", "Hintergrund", "Einschätzung", "Empfehlung"):
        assert h in r.text
    assert "Zeile eins" in r.text and "Zeile zwei" in r.text and "<br" in r.text
    assert f"/ui/bewohner/{rid}" in r.text


async def test_druckansicht_ist_schlicht(client, db_session):
    _, mid = await _meldung(client, db_session)
    t = (await client.get(f"/ui/sbar-meldung/{mid}/druck")).text.lower()
    assert "<script" not in t and "style=" not in t and "<style" not in t and "<img" not in t


async def test_empfaenger_optional_und_escaped(client, db_session):
    _, mid = await _meldung(client, db_session)
    ohne = (await client.get(f"/ui/sbar-meldung/{mid}/druck")).text
    assert "An:" not in ohne
    mit = (await client.get(f"/ui/sbar-meldung/{mid}/druck", params={"an": "Dr. Muster"})).text
    assert "An: Dr. Muster" in mit
    boese = (await client.get(f"/ui/sbar-meldung/{mid}/druck", params={"an": "<b>x</b>"})).text
    assert "<b>x</b>" not in boese and "&lt;b&gt;" in boese


async def test_text_wird_escaped(client, db_session):
    _, mid = await _meldung(client, db_session, situation="<script>alert(1)</script>")
    t = (await client.get(f"/ui/sbar-meldung/{mid}/druck")).text
    assert "<script>alert" not in t


async def test_ansicht_aendert_nichts(client, db_session):
    from sqlalchemy import select
    from apps.api.models.sbar_meldung import SbarMeldung
    _, mid = await _meldung(client, db_session)
    await client.get(f"/ui/sbar-meldung/{mid}/druck")
    assert len((await db_session.execute(select(SbarMeldung))).scalars().all()) == 1


async def test_unbekannte_meldung_404(client):
    assert (await client.get("/ui/sbar-meldung/nope/druck")).status_code == 404


async def test_einstieg_im_profil(client):
    rid = await _person(client)
    t = (await client.get(f"/ui/bewohner/{rid}")).text
    assert f'href="/ui/bewohner/{rid}/sbar-meldung"' in t
