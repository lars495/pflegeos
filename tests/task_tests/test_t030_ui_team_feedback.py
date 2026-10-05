import pytest
from apps.api.main import app
if "/ui/team" not in {r.path for r in app.routes}:
    pytest.skip("T030 noch nicht umgesetzt", allow_module_level=True)
from sqlalchemy import select  # noqa: E402


async def _person(client, **kw):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann", **kw})).json()["id"]


async def _geben(client, n):
    for i in range(n):
        await client.post("/ui/team", data={"gefehlt": f"FEHLT-{i}", "unnoetig": "", "hilft": ""})


async def test_formular(client):
    t = (await client.get("/ui/team")).text
    for f in ("gefehlt", "unnoetig", "hilft"):
        assert f'name="{f}"' in t
    assert 'name="author"' not in t, "Team-Feedback ist anonym"
    assert "anonym" in t.lower()


async def test_unter_mindestanzahl_verborgen(client):
    from apps.api.web import TEAM_MINDESTANZAHL
    assert TEAM_MINDESTANZAHL >= 3
    await _geben(client, TEAM_MINDESTANZAHL - 1)
    t = (await client.get("/ui/team")).text
    assert "FEHLT-0" not in t, "Bei zu wenigen Antworten wären sie zuordenbar"


async def test_ab_mindestanzahl_sichtbar_ohne_zeit(client):
    import re
    import datetime as dt
    from apps.api.web import TEAM_MINDESTANZAHL
    await _geben(client, TEAM_MINDESTANZAHL)
    t = (await client.get("/ui/team")).text
    assert all(f"FEHLT-{i}" in t for i in range(TEAM_MINDESTANZAHL))
    assert not re.search(r"\b\d{1,2}:\d{2}\b", t), "Uhrzeiten machen Antworten zuordenbar"
    assert dt.date.today().strftime("%d.%m.") not in t


async def test_leere_antwort_nicht_gespeichert(client, db_session):
    from apps.api.models.team_feedback import TeamFeedback
    await client.post("/ui/team", data={"gefehlt": " ", "unnoetig": "", "hilft": ""})
    assert (await db_session.execute(select(TeamFeedback))).scalars().all() == []


async def test_navigation(client):
    assert 'href="/ui/team"' in (await client.get("/ui")).text
