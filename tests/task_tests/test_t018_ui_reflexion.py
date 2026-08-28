import pytest

from apps.api.main import app

_pfade = {r.path for r in app.routes}
if "/ui/reflexion" not in _pfade:
    pytest.skip("T018 noch nicht umgesetzt (/ui/reflexion fehlt)", allow_module_level=True)


async def test_formular_wird_angezeigt(client):
    r = await client.get("/ui/reflexion")
    assert r.status_code == 200
    assert "<form" in r.text
    for feld in ("gut", "schwierig", "mitnehmen"):
        assert f'name="{feld}"' in r.text, f"Feld {feld} fehlt"


async def test_privatsphaere_wird_zugesichert(client):
    """Empowerment: Die Pflegekraft muss sehen, dass das nicht in die Akte geht."""
    r = await client.get("/ui/reflexion")
    text = r.text.lower()
    assert "nur f\u00fcr dich" in text or "nicht f\u00fcr die akte" in text


async def test_speichern_legt_reflexion_an(client):
    r = await client.post(
        "/ui/reflexion",
        data={
            "author": "km",
            "gut": "Frau B. hat heute gelacht.",
            "schwierig": "Herr M. wollte nicht aufstehen.",
            "mitnehmen": "Musik hilft.",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    gespeichert = await client.get("/v1/reflections", params={"author": "km"})
    assert len(gespeichert.json()) == 1
    assert gespeichert.json()[0]["gut"] == "Frau B. hat heute gelacht."


async def test_reflexion_ist_privat(client):
    await client.post("/ui/reflexion", data={"author": "km", "gut": "Test"}, follow_redirects=True)
    eintraege = (await client.get("/v1/reflections", params={"author": "km"})).json()
    assert eintraege[0]["nur_fuer_mich"] is True
