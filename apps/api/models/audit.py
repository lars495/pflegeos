from sqlalchemy import Column, DateTime, JSON, String
import uuid
from datetime import datetime

from apps.api.db import Base

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    details = Column(JSON, default=dict)
