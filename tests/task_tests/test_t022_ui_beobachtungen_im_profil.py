"""T022: Beobachtungen erscheinen auf der Profilseite."""
import pytest

pytest.importorskip("apps.api.models.beobachtung", reason="T020 fehlt")
from apps.api.main import app  # noqa: E402

if "/ui/bewohner/{resident_id}/beobachtung" not in {r.path for r in app.routes}:
    pytest.skip("T021 fehlt", allow_module_level=True)
from pathlib import Path  # noqa: E402

if not (Path(__file__).resolve().parents[2] / "apps/api/templates/_beobachtungen.html").exists():
    pytest.skip("T022 noch nicht umgesetzt", allow_module_level=True)


async def _person(client):
    return (await client.post("/v1/residents", json={"name": "Maria Bergmann"})).json()["id"]


async def test_profil_verlinkt_meldung(client):
    rid = await _person(client)
    r = await client.get(f"/ui/bewohner/{rid}")
    assert f"/ui/bewohner/{rid}/beobachtung" in r.text


async def test_beobachtung_erscheint_im_profil(client):
    from apps.api.web import BEOBACHTUNG_KATEGORIEN
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/beobachtung",
                      data={"author": "km", "kategorie": BEOBACHTUNG_KATEGORIEN[1], "notiz": "ganz ruhig heute"})
    r = await client.get(f"/ui/bewohner/{rid}")
    assert BEOBACHTUNG_KATEGORIEN[1] in r.text and "ganz ruhig heute" in r.text


async def test_nur_eigene_person(client):
    from apps.api.web import BEOBACHTUNG_KATEGORIEN
    a, b = await _person(client), await _person(client)
    await client.post(f"/ui/bewohner/{a}/beobachtung",
                      data={"author": "km", "kategorie": BEOBACHTUNG_KATEGORIEN[0], "notiz": "nur bei A"})
    r = await client.get(f"/ui/bewohner/{b}")
    assert "nur bei A" not in r.text


async def test_leerer_zustand(client):
    rid = await _person(client)
    r = await client.get(f"/ui/bewohner/{rid}")
    assert "Keine Beobachtungen" in r.text
