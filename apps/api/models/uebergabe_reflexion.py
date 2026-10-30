from sqlalchemy import Boolean, Column, DateTime, String, Text
import uuid
from datetime import datetime

from apps.api.db import Base


class UebergabeReflexion(Base):
    __tablename__ = "uebergabe_reflexionen"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    author = Column(String, nullable=False, index=True)
    frage = Column(Text, nullable=False)
    antwort = Column(Text, nullable=False)
    geteilt = Column(Boolean, nullable=False, default=False)
    geteilt_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
