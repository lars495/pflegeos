from sqlalchemy import Column, Text, JSON, DateTime, Date, String
import uuid
from datetime import datetime

from apps.api.db import Base

class Resident(Base):
    __tablename__ = "residents"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String, nullable=False)
    geburtsdatum = Column(Date, nullable=True)
    zimmer = Column(String, nullable=True)
    einzugsdatum = Column(Date, nullable=True)
    biografie = Column(Text, default="")
    beruf_frueher = Column(String, nullable=True)
    werte = Column(Text, default="")
    wuensche = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
