from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


class ProcessingTask(Base):
    __tablename__ = "processing_tasks"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), unique=True, nullable=False)
    performed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    work_performed = Column(Text, nullable=False)
    actual_repair_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    actual_packaging_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    actual_labor_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    actual_transport_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_actual_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    return_request = relationship("ReturnRequest", back_populates="processing_task")
    technician = relationship("User", foreign_keys=[performed_by_user_id])

class QualityCheck(Base):
    __tablename__ = "quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), unique=True, nullable=False)
    checked_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    functional_qc_passed = Column(Boolean, default=True, nullable=False)
    cosmetic_grade = Column(String(50), nullable=False, default="GRADE_A")  # GRADE_A, GRADE_B, GRADE_C
    sanitization_passed = Column(Boolean, default=True, nullable=False)
    sanitization_certificate = Column(String(100), nullable=True)
    sanitization_method = Column(String(100), nullable=True)
    qc_notes = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    return_request = relationship("ReturnRequest", back_populates="quality_check")
    inspector = relationship("User", foreign_keys=[checked_by_user_id])

class Disposition(Base):
    __tablename__ = "dispositions"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), unique=True, nullable=False)
    handled_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    disposition_type = Column(String(50), nullable=False)  # RESTOCKED, RETURNED_TO_RETAILER
    inventory_location = Column(String(100), nullable=True)
    realized_resale_value = Column(Numeric(10, 2), nullable=False, default=0.00)
    notes = Column(Text, nullable=True)
    disposed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    return_request = relationship("ReturnRequest", back_populates="disposition")
    handler = relationship("User", foreign_keys=[handled_by_user_id])
