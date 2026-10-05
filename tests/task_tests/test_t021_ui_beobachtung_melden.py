import pytest

from apps.api.main import app

if "/ui/bewohner/{resident_id}/beobachtung" not in {r.path for r in app.routes}:
    pytest.skip("T021 noch nicht umgesetzt", allow_module_level=True)


from sqlalchemy import select


async def _person(client):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann"})).json()["id"]


async def test_formular_zeigt_kategorien(client):
    rid = await _person(client)
    r = await client.get(f"/ui/bewohner/{rid}/beobachtung")
    assert r.status_code == 200
    from apps.api.web import BEOBACHTUNG_KATEGORIEN
    assert len(BEOBACHTUNG_KATEGORIEN) >= 5
    for k in BEOBACHTUNG_KATEGORIEN:
        assert k in r.text
    assert 'name="kategorie"' in r.text and 'name="author"' in r.text


async def test_unbekannt_404(client):
    r = await client.get("/ui/bewohner/nope/beobachtung")
    assert r.status_code == 404


async def test_melden_speichert_und_leitet_weiter(client, db_session):
    from apps.api.models.beobachtung import Beobachtung
    from apps.api.web import BEOBACHTUNG_KATEGORIEN
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/beobachtung", data={
        "author": "km", "kategorie": BEOBACHTUNG_KATEGORIEN[0], "notiz": "seit dem Mittag"},
        follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/ui/bewohner/{rid}"
    rows = (await db_session.execute(select(Beobachtung))).scalars().all()
    assert len(rows) == 1 and rows[0].resident_id == rid and rows[0].notiz == "seit dem Mittag"


async def test_audit_eintrag(client, db_session):
    from apps.api.models.audit import AuditLog
    from apps.api.web import BEOBACHTUNG_KATEGORIEN
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/beobachtung",
                      data={"author": "km", "kategorie": BEOBACHTUNG_KATEGORIEN[0]})
    actions = {e.action for e in (await db_session.execute(select(AuditLog))).scalars()}
    assert "beobachtung.created" in actions


async def test_ohne_kuerzel_oder_kategorie_kein_eintrag(client, db_session):
    from apps.api.models.beobachtung import Beobachtung
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/beobachtung", data={"author": "", "kategorie": ""})
    assert r.status_code == 200
    assert (await db_session.execute(select(Beobachtung))).scalars().all() == []
