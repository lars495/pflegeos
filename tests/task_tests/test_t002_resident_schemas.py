"""T002: Pydantic-Schemas für Residents."""
import pytest
from pydantic import ValidationError

schemas = pytest.importorskip(
    "apps.api.schemas.resident", reason="T002 noch nicht umgesetzt"
)


def test_create_braucht_name():
    with pytest.raises(ValidationError):
        schemas.ResidentCreate()


def test_create_minimal():
    obj = schemas.ResidentCreate(name="Erika Musterfrau")
    assert obj.name == "Erika Musterfrau"


def test_update_alles_optional():
    obj = schemas.ResidentUpdate()
    dumped = obj.model_dump(exclude_unset=True)
    assert dumped == {}, "ResidentUpdate ohne Angaben darf keine Felder setzen"


def test_update_teilupdate():
    obj = schemas.ResidentUpdate(biografie="War Lehrerin in Freiburg.")
    dumped = obj.model_dump(exclude_unset=True)
    assert dumped == {"biografie": "War Lehrerin in Freiburg."}


def test_out_from_attributes():
    class Fake:
        id = "abc123"
        name = "Max Mustermann"
        geburtsdatum = None
        zimmer = None
        einzugsdatum = None
        biografie = ""
        beruf_frueher = None
        werte = ""
        wuensche = []

    out = schemas.ResidentOut.model_validate(Fake())
    assert out.id == "abc123"
    assert out.name == "Max Mustermann"
