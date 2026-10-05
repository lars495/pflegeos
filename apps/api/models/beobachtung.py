from sqlalchemy import Column, DateTime, String, Text
import uuid
from datetime import datetime

from apps.api.db import Base


class Beobachtung(Base):
    __tablename__ = "beobachtungen"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    resident_id = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False)
    kategorie = Column(String, nullable=False)
    notiz = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
