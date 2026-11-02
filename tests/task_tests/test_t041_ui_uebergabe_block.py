import pytest
from apps.api.main import app

if "/ui/bewohner/{resident_id}/uebergabe" not in {r.path for r in app.routes}:
    pytest.skip("T041 noch nicht umgesetzt", allow_module_level=True)

from sqlalchemy import select  # noqa: E402


# ---------- Hilfen: Feldnamen werden aus dem OpenAPI-Schema gelesen, nicht geraten ----------

def _ist_text(prop):
    optionen = prop.get("anyOf", [prop])
    return any(o.get("type") == "string" and "format" not in o and "enum" not in o for o in optionen)


def _ist_liste(prop):
    optionen = prop.get("anyOf", [prop])
    return any(o.get("type") == "array" for o in optionen)


def _body_schema(pfad, methode):
    spec = app.openapi()
    s = spec["paths"][pfad][methode]["requestBody"]["content"]["application/json"]["schema"]
    if "$ref" in s:
        s = spec["components"]["schemas"][s["$ref"].split("/")[-1]]
    return s


def _biografie_payload(text, methode="post", pfad="/v1/residents"):
    props = _body_schema(pfad, methode).get("properties", {})
    for name, prop in props.items():
        if "biograf" in name.lower():
            if _ist_text(prop):
                return {name: text}
            if _ist_liste(prop):
                return {name: [text]}
    raise AssertionError("Kein Biografie-Feld (Text oder Liste) im Resident-Schema gefunden")


def _wunsch_payload(text):
    s = _body_schema("/v1/residents/{resident_id}/wuensche", "post")
    props = s.get("properties", {})
    pflicht = [n for n in s.get("required", []) if n in props and _ist_text(props[n])]
    namen = pflicht or [n for n, p in props.items() if _ist_text(p)][:1]
    assert namen, "Kein Text-Feld im Wunsch-Schema gefunden"
    return {n: text for n in namen}


async def _person(client, name="Maria Bergmann", biografie=None):
    payload = {"name": name}
    if biografie:
        payload.update(_biografie_payload(biografie))
    r = await client.post("/v1/residents", json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def _wunsch(client, rid, text):
    r = await client.post(f"/v1/residents/{rid}/wuensche", json=_wunsch_payload(text))
    assert r.status_code in (200, 201), r.text


# ---------- Tests ----------

async def test_block_ist_aus_profil_vorbefuellt(client):
    rid = await _person(client, biografie="Hat vierzig Jahre als Schneiderin gearbeitet")
    await _wunsch(client, rid, "Morgens in Ruhe Kaffee trinken")
    r = await client.get(f"/ui/bewohner/{rid}/uebergabe")
    assert r.status_code == 200
    assert "Maria Bergmann" in r.text
    assert "Hat vierzig Jahre als Schneiderin gearbeitet" in r.text
    assert "Morgens in Ruhe Kaffee trinken" in r.text
    assert "Vorbefüllt" in r.text


async def test_alle_wuensche_bleiben_sichtbar(client):
    rid = await _person(client)
    await _wunsch(client, rid, "Zum Frühstück Marmeladenbrot")
    await _wunsch(client, rid, "Noch einmal nach Mallorca reisen")
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    assert "Zum Frühstück Marmeladenbrot" in t
    assert "Noch einmal nach Mallorca reisen" in t


async def test_person_zuerst_vor_dem_klinischen(client):
    rid = await _person(client)
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    i_bio = t.index("<h2>Wer ich bin</h2>")
    i_wunsch = t.index("<h2>Das wünsche ich mir</h2>")
    i_wohl = t.index("<h2>Wie es mir heute geht</h2>")
    i_auff = t.index("<h2>Auffälligkeiten</h2>")
    i_notiz = t.index("<h2>Notizen aus der letzten Schicht</h2>")
    assert i_bio < i_wunsch < i_wohl < i_auff < i_notiz


async def test_leere_felder_werden_nicht_erfunden(client):
    rid = await _person(client)
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    assert t.count("Noch nichts eingetragen") >= 3


async def test_hypothese_ist_gekennzeichnet(client):
    rid = await _person(client)
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    assert "Hypothese" in t and "I-PASS" in t


async def test_nur_freigegebene_notizen(client, db_session):
    from apps.api.models.uebergabe_notiz import UebergabeNotiz
    rid = await _person(client)
    db_session.add(UebergabeNotiz(resident_id=rid, author="km", text="Freigegebene Notiz A", status="freigegeben"))
    db_session.add(UebergabeNotiz(resident_id=rid, author="km", text="Entwurf Notiz B", status="entwurf"))
    await db_session.commit()
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    assert "Freigegebene Notiz A" in t
    assert "Entwurf Notiz B" not in t


async def test_beobachtung_wird_gezeigt(client, db_session):
    from apps.api.models.beobachtung import Beobachtung
    rid = await _person(client)
    db_session.add(Beobachtung(resident_id=rid, author="km", kategorie="Trinken", notiz="Hat wenig getrunken"))
    await db_session.commit()
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    assert "Hat wenig getrunken" in t


async def test_daten_anderer_personen_erscheinen_nicht(client, db_session):
    from apps.api.models.uebergabe_notiz import UebergabeNotiz
    a = await _person(client, name="Maria Bergmann", biografie="Biografie von Person A")
    b = await _person(client, name="Hans Winter", biografie="Geheimnis von Person B")
    await _wunsch(client, b, "Wunsch von Person B")
    db_session.add(UebergabeNotiz(resident_id=b, author="km", text="Notiz von Person B", status="freigegeben"))
    await db_session.commit()
    t = (await client.get(f"/ui/bewohner/{a}/uebergabe")).text
    assert "Biografie von Person A" in t
    for fremd in ("Geheimnis von Person B", "Wunsch von Person B", "Notiz von Person B", "Hans Winter"):
        assert fremd not in t


async def test_texte_werden_escaped(client, db_session):
    from apps.api.models.uebergabe_notiz import UebergabeNotiz
    rid = await _person(client)
    db_session.add(UebergabeNotiz(resident_id=rid, author="km", text="<script>alert(1)</script>", status="freigegeben"))
    await db_session.commit()
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    assert "<script>alert(1)</script>" not in t


async def test_ansehen_schreibt_nichts(client, db_session):
    from apps.api.models.uebergabe_profil import UebergabeProfil
    rid = await _person(client, biografie="Original-Biografie")
    await client.get(f"/ui/bewohner/{rid}/uebergabe")
    assert (await db_session.execute(select(UebergabeProfil))).scalars().all() == []


async def test_gespeicherte_fassung_hat_vorrang(client, db_session):
    from apps.api.models.uebergabe_profil import UebergabeProfil
    rid = await _person(client, biografie="Original-Biografie")
    db_session.add(UebergabeProfil(resident_id=rid, biografie="Angepasste Fassung", wohlbefinden="Heute ruhig"))
    await db_session.commit()
    t = (await client.get(f"/ui/bewohner/{rid}/uebergabe")).text
    assert "Angepasste Fassung" in t
    assert "Heute ruhig" in t
    assert "Original-Biografie" not in t


async def test_unbekannte_person_404(client):
    assert (await client.get("/ui/bewohner/nope/uebergabe")).status_code == 404
