import pytest

pytest.importorskip("apps.api.models.uebergabe_reflexion")
from apps.api.main import app  # noqa: E402

if "/ui/uebergabe-frage" not in {r.path for r in app.routes}:
    pytest.skip("T038 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402


async def _alle(db_session):
    from apps.api.models.uebergabe_reflexion import UebergabeReflexion
    db_session.expire_all()
    return (await db_session.execute(select(UebergabeReflexion))).scalars().all()


async def test_seite_zeigt_frage_und_ist_freiwillig(client):
    r = await client.get("/ui/uebergabe-frage")
    assert r.status_code == 200 and "<html" in r.text
    assert "Welche Information" in r.text and "gefehlt" in r.text
    assert "freiwillig" in r.text
    assert "privat" in r.text
    assert "keine Namen" in r.text
    assert 'method="post"' in r.text and 'action="/ui/uebergabe-frage"' in r.text
    assert 'name="author"' in r.text and 'name="antwort"' in r.text


async def test_seite_verlinkt_weitere_bereiche(client):
    t = (await client.get("/ui/uebergabe-frage")).text
    assert 'href="/ui/uebergabe-frage/meine"' in t
    assert 'href="/ui/uebergabe-frage/team"' in t
    assert 'href="/ui/uebergabe"' in t


async def test_antwort_wird_privat_gespeichert(client, db_session):
    r = await client.post("/ui/uebergabe-frage", data={"author": "km", "antwort": "  Letzte Trinkmenge  "})
    assert r.status_code == 200
    assert "privat" in r.text
    assert 'name="antwort"' not in r.text  # nach dem Speichern kein weiteres Formular
    e = (await _alle(db_session))[0]
    assert e.author == "km" and e.antwort == "Letzte Trinkmenge"
    assert e.geteilt is False and e.geteilt_at is None
    assert "Welche Information" in e.frage


async def test_leere_antwort_ist_kein_fehler(client, db_session):
    r1 = await client.post("/ui/uebergabe-frage", data={"author": "km", "antwort": ""})
    r2 = await client.post("/ui/uebergabe-frage", data={"author": "km", "antwort": "   "})
    for r in (r1, r2):
        assert r.status_code == 200
        assert "Kein Problem" in r.text and "freiwillig" in r.text
    assert await _alle(db_session) == []


async def test_ohne_kuerzel_wird_nichts_gespeichert_text_bleibt(client, db_session):
    r = await client.post("/ui/uebergabe-frage", data={"author": "", "antwort": "Wichtiger Gedanke"})
    assert r.status_code == 200
    assert "Kürzel" in r.text
    assert "Wichtiger Gedanke" in r.text  # Text geht nicht verloren
    assert await _alle(db_session) == []


async def test_eingabe_wird_escaped(client):
    r = await client.post("/ui/uebergabe-frage", data={"author": "", "antwort": "<script>alert(1)</script>"})
    assert "<script>alert(1)</script>" not in r.text


async def test_kein_audit_eintrag_privatsphaere(client, db_session):
    from apps.api.models.audit import AuditLog
    await client.post("/ui/uebergabe-frage", data={"author": "km", "antwort": "Etwas Privates"})
    assert (await db_session.execute(select(AuditLog))).scalars().all() == []
