import pytest

pytest.importorskip("apps.api.models.uebergabe_profil")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from apps.api.models.uebergabe_profil import UebergabeProfil  # noqa: E402


def test_tabellenname():
    assert UebergabeProfil.__tablename__ == "uebergabe_profile"


async def test_standardwerte(db_session):
    db_session.add(UebergabeProfil(resident_id="r1"))
    await db_session.commit()
    p = (await db_session.execute(select(UebergabeProfil))).scalars().one()
    assert p.id and len(p.id) > 10
    assert p.biografie is None
    assert p.wuensche is None
    assert p.wohlbefinden is None
    assert p.bearbeitet_von is None
    assert p.updated_at is not None


async def test_leer_und_nicht_angepasst_sind_unterscheidbar(db_session):
    db_session.add(UebergabeProfil(resident_id="r1", biografie="", wuensche=None))
    await db_session.commit()
    db_session.expire_all()
    p = (await db_session.execute(select(UebergabeProfil))).scalars().one()
    assert p.biografie == ""
    assert p.wuensche is None


async def test_felder_speichern(db_session):
    db_session.add(UebergabeProfil(
        resident_id="r1", biografie="Bio", wuensche="Wunsch",
        wohlbefinden="Gut gelaunt", bearbeitet_von="km",
    ))
    await db_session.commit()
    db_session.expire_all()
    p = (await db_session.execute(select(UebergabeProfil))).scalars().one()
    assert (p.biografie, p.wuensche, p.wohlbefinden, p.bearbeitet_von) == ("Bio", "Wunsch", "Gut gelaunt", "km")


async def test_pro_person_nur_eine_zeile(db_session):
    db_session.add(UebergabeProfil(resident_id="r1"))
    await db_session.commit()
    db_session.add(UebergabeProfil(resident_id="r1"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_verschiedene_personen_getrennt(db_session):
    db_session.add(UebergabeProfil(resident_id="r1", biografie="A"))
    db_session.add(UebergabeProfil(resident_id="r2", biografie="B"))
    await db_session.commit()
    zeilen = (await db_session.execute(select(UebergabeProfil))).scalars().all()
    assert {z.resident_id: z.biografie for z in zeilen} == {"r1": "A", "r2": "B"}
