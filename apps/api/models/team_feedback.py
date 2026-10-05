from sqlalchemy import Column, DateTime, String, Text
import uuid
from datetime import datetime

from apps.api.db import Base


class TeamFeedback(Base):
    __tablename__ = "team_feedback"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    gefehlt = Column(Text, default="")
    unnoetig = Column(Text, default="")
    hilft = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
