import json

import pytest

pytest.importorskip("apps.api.models.fruehwarnung")
from sqlalchemy import select  # noqa: E402

from apps.api.models.fruehwarnung import (  # noqa: E402
    STANDARDFRAGEN,
    FruehwarnFrage,
    FruehwarnMeldung,
    standardfragen_sicherstellen,
)


async def test_meldung_defaults(db_session):
    m = FruehwarnMeldung(resident_id="r1", author="hk")
    db_session.add(m)
    await db_session.commit()
    await db_session.refresh(m)
    assert m.id and len(m.id) == 32
    assert m.created_at is not None
    assert m.freitext == ""
    assert m.auffaelligkeiten_liste() == []


async def test_meldung_liste_mit_umlauten(db_session):
    texte = ["Ist müder als sonst", "Hat weniger gegessen"]
    m = FruehwarnMeldung(resident_id="r1", author="hk",
                         auffaelligkeiten=json.dumps(texte, ensure_ascii=False))
    db_session.add(m)
    await db_session.commit()
    await db_session.refresh(m)
    assert m.auffaelligkeiten_liste() == texte


def test_liste_bei_kaputtem_json():
    assert FruehwarnMeldung(auffaelligkeiten="{kaputt").auffaelligkeiten_liste() == []
    assert FruehwarnMeldung(auffaelligkeiten="").auffaelligkeiten_liste() == []
    assert FruehwarnMeldung(auffaelligkeiten=None).auffaelligkeiten_liste() == []


def test_meldung_hat_keine_bewertungsfelder():
    # Jede Stimme zählt gleich: keine Rolle, keine Punktzahl, keine Ampel
    spalten = {c.name for c in FruehwarnMeldung.__table__.columns}
    assert spalten == {"id", "resident_id", "author", "auffaelligkeiten", "freitext", "created_at"}


async def test_frage_defaults(db_session):
    f = FruehwarnFrage(schluessel="eigene_x", text="Isst nur Suppe")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    assert f.id and f.aktiv is True and f.position == 0


async def test_schluessel_ist_eindeutig(db_session):
    from sqlalchemy.exc import IntegrityError
    db_session.add(FruehwarnFrage(schluessel="a", text="A"))
    await db_session.commit()
    db_session.add(FruehwarnFrage(schluessel="a", text="B"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_standardfragen_angelegt(db_session):
    assert len(STANDARDFRAGEN) == 6
    await standardfragen_sicherstellen(db_session)
    fragen = (await db_session.execute(
        select(FruehwarnFrage).order_by(FruehwarnFrage.position))).scalars().all()
    assert len(fragen) == 6
    assert [f.position for f in fragen] == [1, 2, 3, 4, 5, 6]
    assert [f.schluessel for f in fragen] == [s for s, _ in STANDARDFRAGEN]
    assert all(f.aktiv for f in fragen)
    texte = {f.schluessel: f.text for f in fragen}
    assert texte["weniger_gegessen_getrunken"] == "Hat weniger gegessen oder getrunken"
    assert texte["wirkt_anders"] == "Wirkt anders als sonst"


async def test_standardfragen_idempotent_und_respektiert_team(db_session):
    await standardfragen_sicherstellen(db_session)
    f = (await db_session.execute(select(FruehwarnFrage).where(
        FruehwarnFrage.schluessel == "wirkt_anders"))).scalars().one()
    f.aktiv = False
    db_session.add(FruehwarnFrage(schluessel="eigene_1", text="Eigene Frage", position=7))
    await db_session.commit()
    await standardfragen_sicherstellen(db_session)
    db_session.expire_all()
    fragen = (await db_session.execute(select(FruehwarnFrage))).scalars().all()
    assert len(fragen) == 7
    wirkt = [x for x in fragen if x.schluessel == "wirkt_anders"][0]
    assert wirkt.aktiv is False
