"""Fundament der Pflege-Oberfläche: Layout, Assets, Startseite.

Diese Datei prüft, was von Hand gebaut wurde (nicht vom Agenten) —
sie ist die Grundlage, auf der die UI-Tasks aufsetzen.
"""


async def test_startseite_rendert(client):
    r = await client.get("/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Willkommen" in r.text


async def test_layout_regeln_eingehalten(client):
    """Barrierefreiheit ist nicht optional (PRINCIPLES.md)."""
    r = await client.get("/ui")
    assert 'lang="de"' in r.text, "Sprache muss ausgezeichnet sein (Screenreader)"
    assert "Zum Inhalt springen" in r.text, "Skip-Link fehlt"
    assert 'id="inhalt"' in r.text


async def test_keine_externen_ressourcen(client):
    """Kein CDN, keine Web-Fonts — es darf keine Anfrage den Server verlassen."""
    r = await client.get("/ui")
    for muster in ("https://unpkg.com", "https://cdn.", "fonts.googleapis.com", "//cdnjs"):
        assert muster not in r.text, f"Externe Ressource gefunden: {muster}"


async def test_htmx_und_css_lokal_ausgeliefert(client):
    for pfad, teil in (("/static/htmx.min.js", "htmx"), ("/static/style.css", "--accent")):
        r = await client.get(pfad)
        assert r.status_code == 200, f"{pfad} nicht erreichbar"
        assert teil in r.text


async def test_experiment_hinweis_sichtbar(client):
    """Der Disclaimer muss auf jeder Seite stehen — niemand soll echte Daten eingeben."""
    r = await client.get("/ui")
    assert "keine echten Bewohnerdaten" in r.text


def test_initialen_filter():
    from apps.api.web import initialen
    assert initialen("Maria Lieselotte Bergmann") == "MB"
    assert initialen("Max Mustermann") == "MM"
    assert initialen("Cher") == "CH"
    assert initialen("") == "?"
