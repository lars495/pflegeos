from sqlalchemy import Column, DateTime, String, Text
import uuid
from datetime import datetime

from apps.api.db import Base


class SbarNotiz(Base):
    __tablename__ = "sbar_notizen"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    resident_id = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False)
    situation = Column(Text, default="")
    hintergrund = Column(Text, default="")
    einschaetzung = Column(Text, default="")
    empfehlung = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
