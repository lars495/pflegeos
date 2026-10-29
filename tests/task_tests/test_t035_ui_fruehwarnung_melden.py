import pytest
from apps.api.main import app
if "/ui/bewohner/{resident_id}/fruehwarnung" not in {r.path for r in app.routes}:
    pytest.skip("T035 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402

from apps.api.models.audit import AuditLog  # noqa: E402
from apps.api.models.beobachtung import Beobachtung  # noqa: E402
from apps.api.models.fruehwarnung import FruehwarnFrage, FruehwarnMeldung  # noqa: E402
from apps.api.models.uebergabe_notiz import UebergabeNotiz  # noqa: E402

GEGESSEN = "Hat weniger gegessen oder getrunken"


async def _person(client):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann"})).json()["id"]


async def _frage_id(client, db_session, rid, schluessel="weniger_gegessen_getrunken"):
    await client.get(f"/ui/bewohner/{rid}/fruehwarnung")  # legt die Standardfragen an
    db_session.expire_all()
    return (await db_session.execute(
        select(FruehwarnFrage).where(FruehwarnFrage.schluessel == schluessel))).scalars().one().id


async def _meldungen(db_session):
    db_session.expire_all()
    return (await db_session.execute(select(FruehwarnMeldung))).scalars().all()


async def test_formular_zeigt_person_und_standardfragen(client):
    rid = await _person(client)
    r = await client.get(f"/ui/bewohner/{rid}/fruehwarnung")
    assert r.status_code == 200 and "<html" in r.text
    assert "Maria Bergmann" in r.text
    assert GEGESSEN in r.text and "Wirkt anders als sonst" in r.text
    assert 'name="ja"' in r.text and 'name="freitext"' in r.text and 'name="author"' in r.text
    assert "keine Diagnose" in r.text


async def test_unbekannte_person_404(client):
    assert (await client.get("/ui/bewohner/nope/fruehwarnung")).status_code == 404
    assert (await client.post("/ui/bewohner/nope/fruehwarnung",
                              data={"author": "hk", "freitext": "x"})).status_code == 404
    assert (await client.post("/ui/bewohner/nope/fruehwarnung/fragen",
                              data={"text": "x"})).status_code == 404


async def test_meldung_speichern(client, db_session):
    rid = await _person(client)
    fid = await _frage_id(client, db_session, rid)
    r = await client.post(f"/ui/bewohner/{rid}/fruehwarnung",
                          data={"author": "hk", "ja": [fid], "freitext": "Mag keinen Tee mehr"})
    assert r.status_code == 200 and "gespeichert" in r.text
    m = (await _meldungen(db_session))[0]
    assert m.resident_id == rid and m.author == "hk"
    assert m.auffaelligkeiten_liste() == [GEGESSEN]
    assert m.freitext == "Mag keinen Tee mehr"


async def test_nur_freitext_reicht(client, db_session):
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/fruehwarnung",
                          data={"author": "hk", "freitext": "Wirkt still"})
    assert r.status_code == 200 and "gespeichert" in r.text
    ms = await _meldungen(db_session)
    assert len(ms) == 1 and ms[0].auffaelligkeiten_liste() == []


async def test_leer_oder_ohne_kuerzel_speichert_nichts(client, db_session):
    rid = await _person(client)
    fid = await _frage_id(client, db_session, rid)
    r1 = await client.post(f"/ui/bewohner/{rid}/fruehwarnung",
                           data={"author": "", "ja": [fid], "freitext": "x"})
    r2 = await client.post(f"/ui/bewohner/{rid}/fruehwarnung",
                           data={"author": "hk", "freitext": "  "})
    assert r1.status_code == 200 and "Kürzel" in r1.text
    assert r2.status_code == 200 and "gespeichert" not in r2.text
    assert await _meldungen(db_session) == []


async def test_audit_ohne_inhalt(client, db_session):
    rid = await _person(client)
    fid = await _frage_id(client, db_session, rid)
    await client.post(f"/ui/bewohner/{rid}/fruehwarnung",
                      data={"author": "hk", "ja": [fid], "freitext": "GEHEIMER-INHALT"})
    eintraege = (await db_session.execute(select(AuditLog))).scalars().all()
    assert "fruehwarnung.gemeldet" in {e.action for e in eintraege}
    for e in eintraege:
        for spalte in e.__table__.columns:
            wert = str(getattr(e, spalte.name))
            assert "GEHEIMER-INHALT" not in wert
            assert GEGESSEN not in wert


async def test_keine_automatische_folge(client, db_session):
    # Pflegekraft entscheidet: aus einer Meldung entsteht nichts von selbst
    rid = await _person(client)
    fid = await _frage_id(client, db_session, rid)
    await client.post(f"/ui/bewohner/{rid}/fruehwarnung",
                      data={"author": "hk", "ja": [fid], "freitext": "x"})
    assert (await db_session.execute(select(Beobachtung))).scalars().all() == []
    assert (await db_session.execute(select(UebergabeNotiz))).scalars().all() == []


async def test_ausgeschaltete_frage_wird_nicht_angeboten_und_ignoriert(client, db_session):
    rid = await _person(client)
    fid = await _frage_id(client, db_session, rid)
    url = f"/ui/bewohner/{rid}/fruehwarnung"
    assert f'id="frage-{fid}"' in (await client.get(url)).text
    r = await client.post(f"{url}/fragen/{fid}/umschalten", follow_redirects=True)
    assert r.status_code == 200 and f'id="frage-{fid}"' not in r.text
    db_session.expire_all()
    frage = (await db_session.execute(select(FruehwarnFrage).where(FruehwarnFrage.id == fid))).scalars().one()
    assert frage.aktiv is False
    await client.post(url, data={"author": "hk", "ja": [fid, "nope"], "freitext": "x"})
    m = (await _meldungen(db_session))[0]
    assert m.auffaelligkeiten_liste() == [] and m.freitext == "x"
    r = await client.post(f"{url}/fragen/{fid}/umschalten", follow_redirects=True)
    assert f'id="frage-{fid}"' in r.text


async def test_alte_meldung_behaelt_ihren_text(client, db_session):
    rid = await _person(client)
    fid = await _frage_id(client, db_session, rid)
    url = f"/ui/bewohner/{rid}/fruehwarnung"
    await client.post(url, data={"author": "hk", "ja": [fid]})
    await client.post(f"{url}/fragen/{fid}/umschalten", follow_redirects=True)
    assert (await _meldungen(db_session))[0].auffaelligkeiten_liste() == [GEGESSEN]


async def test_eigene_frage_hinzufuegen(client, db_session):
    rid = await _person(client)
    await _frage_id(client, db_session, rid)
    url = f"/ui/bewohner/{rid}/fruehwarnung/fragen"
    r = await client.post(url, data={"text": "Isst nur noch Suppe"}, follow_redirects=True)
    assert r.status_code == 200 and "Isst nur noch Suppe" in r.text
    db_session.expire_all()
    fragen = (await db_session.execute(select(FruehwarnFrage))).scalars().all()
    eigene = [f for f in fragen if f.schluessel.startswith("eigene_")]
    assert len(eigene) == 1 and eigene[0].aktiv is True and eigene[0].text == "Isst nur noch Suppe"
    assert eigene[0].position == max(f.position for f in fragen)
    assert f'id="frage-{eigene[0].id}"' in r.text
    assert "fruehwarnung.frage_geaendert" in {
        e.action for e in (await db_session.execute(select(AuditLog))).scalars()}


async def test_leere_eigene_frage_wird_nicht_angelegt(client, db_session):
    rid = await _person(client)
    await _frage_id(client, db_session, rid)
    await client.post(f"/ui/bewohner/{rid}/fruehwarnung/fragen", data={"text": "   "},
                      follow_redirects=True)
    db_session.expire_all()
    assert len((await db_session.execute(select(FruehwarnFrage))).scalars().all()) == 6


async def test_unbekannte_frage_umschalten_404(client):
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/fruehwarnung/fragen/nope/umschalten")
    assert r.status_code == 404
