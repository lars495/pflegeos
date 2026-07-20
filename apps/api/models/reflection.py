from sqlalchemy import Column, Text, Boolean, DateTime, String
import uuid
from datetime import datetime

from apps.api.db import Base

class Reflection(Base):
    __tablename__ = "reflections"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    author = Column(String, nullable=False)
    gut = Column(Text, default="")
    schwierig = Column(Text, default="")
    mitnehmen = Column(Text, default="")
    nur_fuer_mich = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
