from sqlalchemy import Column, DateTime, String, Text
import uuid
from datetime import datetime

from apps.api.db import Base


class UebergabeNotiz(Base):
    __tablename__ = "uebergabe_notizen"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    resident_id = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String, default="entwurf")
    freigegeben_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
