from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


class RetailerDecision(Base):
    __tablename__ = "retailer_decisions"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True)
    decided_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision = Column(String(50), nullable=False)  # APPROVED, REJECTED, CHANGED
    approved_option = Column(String(50), nullable=False)  # REFURBISH, REPAIR, RESALE_AS_IS, RETURN_TO_RETAILER, RECYCLE
    remarks = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    return_request = relationship("ReturnRequest", back_populates="decisions")
    decider = relationship("User", foreign_keys=[decided_by_user_id])
