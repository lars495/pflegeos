from sqlalchemy import Column, DateTime, String, Text
import uuid
from datetime import datetime

from apps.api.db import Base


class UebergabeProfil(Base):
    """
    Von der Pflegekraft angepasste Fassung des Übergabe-Blocks.
    None bedeutet: nicht angepasst – es gilt live der Wert aus dem Bewohnerprofil.
    Ein leerer Text "" bedeutet: bewusst leer gelassen.
    Diese beiden Zustände müssen unterscheidbar bleiben; nichts darf "" zu None umwandeln.
    """
    __tablename__ = "uebergabe_profile"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    resident_id = Column(String, nullable=False, unique=True, index=True)
    biografie = Column(Text, nullable=True)
    wuensche = Column(Text, nullable=True)
    wohlbefinden = Column(Text, nullable=True)
    bearbeitet_von = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
