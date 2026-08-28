"""Prüft, dass Funktionen für Menschen ERREICHBAR sind — nicht nur, dass
ihre Endpunkte antworten.

Hintergrund: T016 und T017 waren grün (Endpunkte + Fragmente korrekt),
aber niemand konnte sie benutzen — die Profilseite band die Fragmente
nicht ein. Grüne Tests sind kein Ersatz dafür, einmal hinzuschauen.
"""

import pytest


async def _person(client, **rest):
    r = await client.post("/v1/residents", json={"name": "Maria Bergmann", **rest})
    return r.json()["id"]


async def test_profil_hat_bearbeiten_knopf(client):
    """Die Biografie muss von der Profilseite aus bearbeitbar sein."""
    rid = await _person(client, biografie="War Lehrerin.")
    r = await client.get(f"/ui/bewohner/{rid}")
    assert f'hx-get="/ui/bewohner/{rid}/biografie"' in r.text, \
        "Kein Bearbeiten-Knopf auf der Profilseite"


async def test_profil_hat_wunsch_formular(client):
    """Wünsche müssen direkt auf der Profilseite festgehalten werden können."""
    rid = await _person(client)
    r = await client.get(f"/ui/bewohner/{rid}")
    assert f'hx-post="/ui/bewohner/{rid}/wuensche"' in r.text, \
        "Kein Wunsch-Formular auf der Profilseite"
    assert 'name="wunsch"' in r.text


async def test_htmx_wird_geladen(client):
    """Ohne HTMX im Layout bleiben alle hx-Attribute wirkungslos."""
    rid = await _person(client)
    r = await client.get(f"/ui/bewohner/{rid}")
    assert "/static/htmx.min.js" in r.text


async def test_wunsch_erscheint_nach_dem_speichern(client):
    """Der ganze Weg: Wunsch eintragen → er steht auf der Profilseite."""
    rid = await _person(client)
    await client.post(f"/ui/bewohner/{rid}/wuensche", data={"wunsch": "Einmal wieder ans Meer"})
    r = await client.get(f"/ui/bewohner/{rid}")
    assert "Einmal wieder ans Meer" in r.text


async def test_jede_seite_ist_erreichbar(client):
    """Kein toter Link in der Navigation."""
    rid = await _person(client)
    for pfad in ("/ui", "/ui/bewohner", "/ui/bewohner/neu", "/ui/reflexion",
                 "/ui/reflexion/meine", f"/ui/bewohner/{rid}"):
        r = await client.get(pfad)
        assert r.status_code == 200, f"{pfad} antwortet mit {r.status_code}"
