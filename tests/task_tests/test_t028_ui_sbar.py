import pytest
from apps.api.main import app
if "/ui/bewohner/{resident_id}/sbar" not in {r.path for r in app.routes}:
    pytest.skip("T028 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402


async def _person(client, **kw):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann", **kw})).json()["id"]


async def test_vorbefuellung_aus_daten(client):
    from apps.api.web import BEOBACHTUNG_KATEGORIEN
    rid = await _person(client, zimmer="214", biografie="Lehrerin aus Freiburg.")
    await client.post(f"/ui/bewohner/{rid}/beobachtung",
                      data={"author": "km", "kategorie": BEOBACHTUNG_KATEGORIEN[1], "notiz": "seit gestern"})
    t = (await client.get(f"/ui/bewohner/{rid}/sbar")).text
    for teil in (BEOBACHTUNG_KATEGORIEN[1], "seit gestern", "214", "Lehrerin aus Freiburg"):
        assert teil in t, teil
    for feld in ("situation", "hintergrund", "einschaetzung", "empfehlung", "author"):
        assert f'name="{feld}"' in t


async def test_einschaetzung_schreibt_die_pflegekraft(client):
    """Empowerment: Einschätzung und Empfehlung kommen von der Pflegekraft, nicht von der Software."""
    import re
    rid = await _person(client)
    t = (await client.get(f"/ui/bewohner/{rid}/sbar")).text
    for feld in ("einschaetzung", "empfehlung"):
        m = re.search(r'<textarea[^>]*name="%s"[^>]*>(.*?)</textarea>' % feld, t, re.S)
        assert m and m.group(1).strip() == "", f"{feld} muss leer vorgegeben sein"


async def test_speichern(client, db_session):
    from apps.api.models.sbar import SbarNotiz
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/sbar", data={"author": "km", "situation": "S",
        "hintergrund": "B", "einschaetzung": "A", "empfehlung": "R"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/ui/bewohner/{rid}"
    rows = (await db_session.execute(select(SbarNotiz))).scalars().all()
    assert len(rows) == 1 and rows[0].empfehlung == "R"


async def test_ohne_kuerzel_nicht_gespeichert(client, db_session):
    from apps.api.models.sbar import SbarNotiz
    rid = await _person(client)
    r = await client.post(f"/ui/bewohner/{rid}/sbar", data={"author": "", "situation": "S"})
    assert r.status_code == 200
    assert (await db_session.execute(select(SbarNotiz))).scalars().all() == []


async def test_link_im_profil(client):
    rid = await _person(client)
    assert f"/ui/bewohner/{rid}/sbar" in (await client.get(f"/ui/bewohner/{rid}")).text
