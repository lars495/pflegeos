from pydantic import BaseModel, ConfigDict
import datetime as dt

class ResidentCreate(BaseModel):
    name: str
    geburtsdatum: dt.date | None = None
    zimmer: str | None = None
    einzugsdatum: dt.date | None = None
    biografie: str = ""
    beruf_frueher: str | None = None
    werte: str = ""
    wuensche: list[str] = []

class ResidentUpdate(BaseModel):
    name: str | None = None
    geburtsdatum: dt.date | None = None
    zimmer: str | None = None
    einzugsdatum: dt.date | None = None
    biografie: str | None = None
    beruf_frueher: str | None = None
    werte: str | None = None
    wuensche: list[str] | None = None

class ResidentOut(BaseModel):
    id: str
    name: str
    geburtsdatum: dt.date | None = None
    zimmer: str | None = None
    einzugsdatum: dt.date | None = None
    biografie: str = ""
    beruf_frueher: str | None = None
    werte: str = ""
    wuensche: list[str] = []

    model_config = ConfigDict(from_attributes=True)
