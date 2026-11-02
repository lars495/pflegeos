import pytest
from apps.api.main import app


def _hat_post(pfad):
    return any(
        getattr(r, "path", None) == pfad and "POST" in (getattr(r, "methods", None) or set())
        for r in app.routes
    )


if not _hat_post("/ui/bewohner/{resident_id}/uebergabe"):
    pytest.skip("T042 noch nicht umgesetzt", allow_module_level=True)

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
    raise AssertionError("Kein Biografie-Feld (Text oder Liste) im Schema gefunden")


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


def _url(rid):
    return f"/ui/bewohner/{rid}/uebergabe"


# ---------- Tests ----------

async def test_formular_ist_auf_der_seite(client):
    rid = await _person(client)
    t = (await client.get(_url(rid))).text
    assert f'action="{_url(rid)}"' in t
    assert 'method="post"' in t.lower()
    for feld in ("author", "biografie", "wuensche", "wohlbefinden"):
        assert f'name="{feld}"' in t


async def test_formular_ist_vorbefuellt(client):
    rid = await _person(client, biografie="Original-Biografie")
    t = (await client.get(_url(rid))).text
    assert "Original-Biografie" in t


async def test_speichern_und_anzeigen(client, db_session):
    from apps.api.models.uebergabe_profil import UebergabeProfil
    rid = await _person(client, biografie="Original-Biografie")
    r = await client.post(_url(rid), data={
        "author": "km", "biografie": "Hat als Schneiderin gearbeitet",
        "wuensche": "Abends Radio hören", "wohlbefinden": "Heute fröhlich",
    })
    assert r.status_code == 303
    assert r.headers["location"].endswith(_url(rid))
    t = (await client.get(_url(rid))).text
    assert "Hat als Schneiderin gearbeitet" in t
    assert "Abends Radio hören" in t
    assert "Heute fröhlich" in t
    assert "Original-Biografie" not in t
    p = (await db_session.execute(select(UebergabeProfil))).scalars().one()
    assert p.bearbeitet_von == "km"


async def test_profil_und_wuensche_bleiben_unveraendert(client):
    rid = await _person(client, biografie="Original-Biografie")
    w = await client.post(f"/v1/residents/{rid}/wuensche", json=_wunsch_payload("Morgens Kaffee am Fenster"))
    assert w.status_code in (200, 201), w.text
    await client.post(_url(rid), data={"author": "km", "biografie": "Andere Fassung",
                                       "wuensche": "Andere Wünsche", "wohlbefinden": ""})
    assert "Original-Biografie" in (await client.get(f"/v1/residents/{rid}")).text
    assert "Morgens Kaffee am Fenster" in (await client.get(f"/v1/residents/{rid}/wuensche")).text


async def test_ohne_kuerzel_wird_nichts_gespeichert(client, db_session):
    from apps.api.models.uebergabe_profil import UebergabeProfil
    rid = await _person(client)
    r = await client.post(_url(rid), data={"author": "  ", "biografie": "x", "wuensche": "y", "wohlbefinden": "z"})
    assert r.status_code == 422
    assert "Kürzel" in r.text
    assert (await db_session.execute(select(UebergabeProfil))).scalars().all() == []


async def test_unveraendert_bleibt_live_aus_dem_profil(client, db_session):
    from apps.api.models.uebergabe_profil import UebergabeProfil
    rid = await _person(client, biografie="Original-Biografie")
    # Browser schicken Zeilenumbrüche als \r\n — darf nicht als Änderung zählen
    r = await client.post(_url(rid), data={"author": "km", "biografie": "Original-Biografie\r\n",
                                           "wuensche": "", "wohlbefinden": "Heute müde"})
    assert r.status_code == 303
    db_session.expire_all()
    p = (await db_session.execute(select(UebergabeProfil))).scalars().one()
    assert p.biografie is None
    assert p.wuensche is None
    assert p.wohlbefinden == "Heute müde"
    # Profil ändert sich später → Übergabe zeigt die neue Fassung
    patch = await client.patch(
        f"/v1/residents/{rid}",
        json=_biografie_payload("Neue Biografie", "patch", "/v1/residents/{resident_id}"),
    )
    assert patch.status_code == 200, patch.text
    t = (await client.get(_url(rid))).text
    assert "Neue Biografie" in t
    assert "Heute müde" in t


async def test_bewusstes_leeren_ist_erlaubt(client, db_session):
    from apps.api.models.uebergabe_profil import UebergabeProfil
    rid = await _person(client, biografie="Original-Biografie")
    await client.post(_url(rid), data={"author": "km", "biografie": "", "wuensche": "", "wohlbefinden": ""})
    db_session.expire_all()
    p = (await db_session.execute(select(UebergabeProfil))).scalars().one()
    assert p.biografie == ""
    t = (await client.get(_url(rid))).text
    assert "Original-Biografie" not in t


async def test_zweites_speichern_aktualisiert_dieselbe_zeile(client, db_session):
    from apps.api.models.uebergabe_profil import UebergabeProfil
    rid = await _person(client)
    await client.post(_url(rid), data={"author": "km", "biografie": "", "wuensche": "", "wohlbefinden": "erste Fassung"})
    await client.post(_url(rid), data={"author": "ab", "biografie": "", "wuensche": "", "wohlbefinden": "zweite Fassung"})
    db_session.expire_all()
    p = (await db_session.execute(select(UebergabeProfil))).scalars().one()
    assert p.wohlbefinden == "zweite Fassung"
    assert p.bearbeitet_von == "ab"


async def test_audit_ohne_inhalt(client, db_session):
    from apps.api.models.audit import AuditLog
    rid = await _person(client)
    await client.post(_url(rid), data={"author": "km", "biografie": "Geheime Lebensgeschichte",
                                       "wuensche": "", "wohlbefinden": ""})
    eintraege = (await db_session.execute(select(AuditLog))).scalars().all()
    passende = [e for e in eintraege if e.action == "uebergabe_profil.bearbeitet"]
    assert len(passende) == 1
    assert "Geheime Lebensgeschichte" not in str(vars(passende[0]))


async def test_anpassung_gilt_nur_fuer_diese_person(client):
    a = await _person(client, name="Maria Bergmann")
    b = await _person(client, name="Hans Winter")
    await client.post(_url(a), data={"author": "km", "biografie": "Nur für A", "wuensche": "", "wohlbefinden": ""})
    assert "Nur für A" not in (await client.get(_url(b))).text


async def test_eingaben_werden_escaped(client):
    rid = await _person(client)
    await client.post(_url(rid), data={"author": "km", "biografie": "<script>alert(1)</script>",
                                       "wuensche": "", "wohlbefinden": ""})
    t = (await client.get(_url(rid))).text
    assert "<script>alert(1)</script>" not in t


async def test_unbekannte_person_404(client):
    r = await client.post("/ui/bewohner/nope/uebergabe", data={"author": "km"})
    assert r.status_code == 404
