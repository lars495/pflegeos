import pytest

pytest.importorskip("apps.api.models.uebergabe_reflexion")
from apps.api.main import app  # noqa: E402

if "/ui/uebergabe-frage/team" not in {r.path for r in app.routes}:
    pytest.skip("T039 noch nicht umgesetzt", allow_module_level=True)
import datetime as dt  # noqa: E402
from sqlalchemy import select  # noqa: E402


async def _neu(db_session, author, antwort, geteilt=False):
    from apps.api.models.uebergabe_reflexion import UebergabeReflexion
    e = UebergabeReflexion(
        author=author, frage="Welche Information hat gefehlt?", antwort=antwort,
        geteilt=geteilt, geteilt_at=dt.datetime.utcnow() if geteilt else None,
    )
    db_session.add(e)
    await db_session.commit()
    return e.id


async def _lade(db_session, eid):
    from apps.api.models.uebergabe_reflexion import UebergabeReflexion
    db_session.expire_all()
    return (await db_session.execute(select(UebergabeReflexion).where(UebergabeReflexion.id == eid))).scalars().one()


async def test_meine_ohne_kuerzel_zeigt_nichts(client, db_session):
    await _neu(db_session, "km", "Geheimer Gedanke A")
    r = await client.get("/ui/uebergabe-frage/meine")
    assert r.status_code == 200 and "<html" in r.text
    assert 'name="author"' in r.text
    assert "Geheimer Gedanke A" not in r.text


async def test_meine_zeigt_nur_eigene(client, db_session):
    eid = await _neu(db_session, "km", "Eigener Punkt")
    await _neu(db_session, "zz", "Fremder Punkt")
    r = await client.get("/ui/uebergabe-frage/meine", params={"author": "km"})
    assert r.status_code == 200
    assert "Eigener Punkt" in r.text and "Fremder Punkt" not in r.text
    assert f'action="/ui/uebergabe-frage/{eid}/teilen"' in r.text
    assert "Privat" in r.text


async def test_teilen_nur_mit_ausdruecklicher_aktion(client, db_session):
    eid = await _neu(db_session, "km", "Punkt X")
    # Allein das Ansehen teilt nichts.
    await client.get("/ui/uebergabe-frage/meine", params={"author": "km"})
    assert (await _lade(db_session, eid)).geteilt is False
    r = await client.post(f"/ui/uebergabe-frage/{eid}/teilen", data={"author": "km"})
    assert r.status_code == 303
    assert "/ui/uebergabe-frage/meine" in r.headers["location"] and "author=km" in r.headers["location"]
    e = await _lade(db_session, eid)
    assert e.geteilt is True and e.geteilt_at is not None


async def test_falsches_kuerzel_darf_nicht_teilen(client, db_session):
    eid = await _neu(db_session, "km", "Punkt Y")
    r = await client.post(f"/ui/uebergabe-frage/{eid}/teilen", data={"author": "zz"})
    assert r.status_code == 403
    r = await client.post(f"/ui/uebergabe-frage/{eid}/teilen", data={})
    assert r.status_code == 403
    assert (await _lade(db_session, eid)).geteilt is False


async def test_unbekannter_eintrag_404(client):
    assert (await client.post("/ui/uebergabe-frage/nope/teilen", data={"author": "km"})).status_code == 404
    assert (await client.post("/ui/uebergabe-frage/nope/zuruecknehmen", data={"author": "km"})).status_code == 404


async def test_zuruecknehmen(client, db_session):
    eid = await _neu(db_session, "km", "Punkt Z", geteilt=True)
    r = await client.post(f"/ui/uebergabe-frage/{eid}/zuruecknehmen", data={"author": "zz"})
    assert r.status_code == 403
    assert (await _lade(db_session, eid)).geteilt is True
    r = await client.post(f"/ui/uebergabe-frage/{eid}/zuruecknehmen", data={"author": "km"})
    assert r.status_code == 303
    e = await _lade(db_session, eid)
    assert e.geteilt is False and e.geteilt_at is None
    team = (await client.get("/ui/uebergabe-frage/team")).text
    assert "Punkt Z" not in team


async def test_team_sicht_nur_geteilt_und_anonym(client, db_session):
    await _neu(db_session, "zq7", "Geteilter Punkt A", geteilt=True)
    await _neu(db_session, "xw4", "Geteilter Punkt B", geteilt=True)
    await _neu(db_session, "zq7", "Privater Punkt C", geteilt=False)
    r = await client.get("/ui/uebergabe-frage/team")
    assert r.status_code == 200 and "<html" in r.text
    assert "Geteilter Punkt A" in r.text and "Geteilter Punkt B" in r.text
    assert "Privater Punkt C" not in r.text
    assert "zq7" not in r.text and "xw4" not in r.text  # keine Kürzel
    assert "anonym" in r.text and "freiwillig" in r.text
    assert "Das Team entscheidet" in r.text


async def test_team_sicht_leer(client):
    r = await client.get("/ui/uebergabe-frage/team")
    assert r.status_code == 200 and "Noch nichts geteilt" in r.text


async def test_texte_werden_escaped(client, db_session):
    await _neu(db_session, "km", "<b>fett</b>", geteilt=True)
    t = (await client.get("/ui/uebergabe-frage/team")).text
    assert "<b>fett</b>" not in t and "&lt;b&gt;" in t


async def test_kein_audit_beim_teilen(client, db_session):
    from apps.api.models.audit import AuditLog
    eid = await _neu(db_session, "km", "Punkt Q")
    await client.post(f"/ui/uebergabe-frage/{eid}/teilen", data={"author": "km"})
    await client.post(f"/ui/uebergabe-frage/{eid}/zuruecknehmen", data={"author": "km"})
    assert (await db_session.execute(select(AuditLog))).scalars().all() == []


async def test_uebergabe_seite_verlinkt_frage_freiwillig(client):
    r = await client.get("/ui/uebergabe")
    assert r.status_code == 200
    assert 'href="/ui/uebergabe-frage"' in r.text
    assert "freiwillig" in r.text
