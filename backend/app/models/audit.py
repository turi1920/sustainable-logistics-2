from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


class ReturnStatusHistory(Base):
    __tablename__ = "return_status_history"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    actor_username = Column(String(100), nullable=False)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    return_request = relationship("ReturnRequest", back_populates="status_history")
