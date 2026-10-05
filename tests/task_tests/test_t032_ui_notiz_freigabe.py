import pytest
from apps.api.main import app
if "/ui/bewohner/{resident_id}/notizen" not in {r.path for r in app.routes}:
    pytest.skip("T032 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402


async def _person(client, **kw):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann", **kw})).json()["id"]


async def test_entwurf_anlegen(client, db_session):
    from apps.api.models.uebergabe_notiz import UebergabeNotiz
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/notizen", data={"author": "km", "text": "Hat gut geschlafen"})
    assert r.status_code == 200 and "<html" not in r.text
    assert "Hat gut geschlafen" in r.text and "Entwurf" in r.text
    n = (await db_session.execute(select(UebergabeNotiz))).scalars().one()
    assert n.status == "entwurf"


async def test_freigeben(client, db_session):
    from apps.api.models.uebergabe_notiz import UebergabeNotiz
    from apps.api.models.audit import AuditLog
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/notizen", data={"author": "km", "text": "Notiz A"})
    nid = (await db_session.execute(select(UebergabeNotiz))).scalars().one().id
    r = await client.post(f"/ui/notizen/{nid}/freigeben")
    assert r.status_code == 200 and "Freigegeben" in r.text
    db_session.expire_all()
    n = (await db_session.execute(select(UebergabeNotiz))).scalars().one()
    assert n.status == "freigegeben" and n.freigegeben_at is not None
    assert "notiz.freigegeben" in {e.action for e in (await db_session.execute(select(AuditLog))).scalars()}


async def test_ohne_text_oder_kuerzel_nichts(client, db_session):
    from apps.api.models.uebergabe_notiz import UebergabeNotiz
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/notizen", data={"author": "", "text": "x"})
    await client.post(f"/ui/bewohner/{rid}/notizen", data={"author": "km", "text": " "})
    assert (await db_session.execute(select(UebergabeNotiz))).scalars().all() == []


async def test_im_profil(client):
    rid = await _person(client)
    t = (await client.get(f"/ui/bewohner/{rid}")).text
    assert f'hx-post="/ui/bewohner/{rid}/notizen"' in t


async def test_unbekannte_notiz_404(client):
    assert (await client.post("/ui/notizen/nope/freigeben")).status_code == 404
