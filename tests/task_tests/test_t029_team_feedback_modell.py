"""T029: Modell TeamFeedback."""
import pytest
mod = pytest.importorskip("apps.api.models.team_feedback", reason="T029 noch nicht umgesetzt")


def test_tabelle():
    assert mod.TeamFeedback.__tablename__ == "team_feedback"
    assert {"id", "gefehlt", "unnoetig", "hilft", "created_at"} <= {c.name for c in mod.TeamFeedback.__table__.columns}


async def test_persistenz(db_session):
    o = mod.TeamFeedback(gefehlt="Infos zur Nacht")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    assert o.id and o.created_at is not None


def test_anonym_by_design():
    """Kein Feld darf auf eine Person zurückführen."""
    cols = {c.name for c in mod.TeamFeedback.__table__.columns}
    assert not cols & {"author", "user", "user_id", "kuerzel", "name", "ip"}

