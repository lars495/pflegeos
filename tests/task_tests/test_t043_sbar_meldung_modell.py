import pytest

pytest.importorskip("apps.api.models.sbar_meldung")
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from apps.api.models.sbar_meldung import SbarMeldung  # noqa: E402


def test_tabellenname():
    assert SbarMeldung.__tablename__ == "sbar_meldungen"


async def test_anlegen_mit_defaults(db_session):
    db_session.add(SbarMeldung(resident_id="r1", author="km"))
    await db_session.commit()
    m = (await db_session.execute(select(SbarMeldung))).scalars().one()
    assert isinstance(m.id, str) and len(m.id) == 32
    assert m.created_at is not None
    assert m.fruehwarnung_id is None
    for feld in ("situation", "hintergrund", "einschaetzung", "empfehlung"):
        assert getattr(m, feld) == ""


async def test_alle_felder_speichern(db_session):
    db_session.add(SbarMeldung(
        resident_id="r1", fruehwarnung_id="fw1", author="km",
        situation="S", hintergrund="B", einschaetzung="A", empfehlung="R",
    ))
    await db_session.commit()
    m = (await db_session.execute(select(SbarMeldung))).scalars().one()
    assert (m.fruehwarnung_id, m.situation, m.hintergrund, m.einschaetzung, m.empfehlung) == ("fw1", "S", "B", "A", "R")


async def test_ohne_bewohner_nicht_speicherbar(db_session):
    db_session.add(SbarMeldung(author="km"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_ohne_kuerzel_nicht_speicherbar(db_session):
    db_session.add(SbarMeldung(resident_id="r1"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
