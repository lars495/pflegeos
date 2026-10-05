import pytest
from apps.api.main import app
if "/ui/bewohner/{resident_id}/hinweise" not in {r.path for r in app.routes}:
    pytest.skip("T025 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402


async def _person(client, **kw):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann", **kw})).json()["id"]


async def test_hinweis_speichern_fragment(client, db_session):
    from apps.api.models.hinweis import PersonHinweis
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/hinweise", data={"text": "Bitte nicht vor Besuch besprechen"})
    assert r.status_code == 200 and "<html" not in r.text
    assert "Bitte nicht vor Besuch besprechen" in r.text
    assert len((await db_session.execute(select(PersonHinweis))).scalars().all()) == 1


async def test_leerer_hinweis_ignoriert(client, db_session):
    from apps.api.models.hinweis import PersonHinweis
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/hinweise", data={"text": "  "})
    assert (await db_session.execute(select(PersonHinweis))).scalars().all() == []


async def test_profil_zeigt_formular_und_hinweis(client):
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/hinweise", data={"text": "Morgens brauche ich Zeit"})
    t = (await client.get(f"/ui/bewohner/{rid}")).text
    assert f'hx-post="/ui/bewohner/{rid}/hinweise"' in t
    assert "Morgens brauche ich Zeit" in t
    assert "Das ist mir bei Übergaben wichtig" in t


async def test_unbekannt_404(client):
    assert (await client.post("/ui/bewohner/nope/hinweise", data={"text": "x"})).status_code == 404
