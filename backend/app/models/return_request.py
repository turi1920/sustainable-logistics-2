from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


class ReturnRequest(Base):
    __tablename__ = "returns"

    id = Column(String(50), primary_key=True, index=True)  # e.g. RET-1001
    order_ref = Column(String(100), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_category = Column(String(100), nullable=False, default="Smartphone")
    product_name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=False)
    serial_expected = Column(String(100), nullable=True, index=True)
    serial_received = Column(String(100), nullable=True, index=True)
    customer_pincode = Column(String(20), nullable=True)
    return_reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="RETURN_REQUESTED", index=True)
    storage_location = Column(String(100), nullable=True)
    package_condition = Column(String(255), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    pickup_partner_id = Column(Integer, ForeignKey("pickup_partners.id", ondelete="SET NULL"), nullable=True)
    pickup_status = Column(String(50), nullable=False, default="PENDING_ASSIGNMENT")
    pickup_scheduled_date = Column(DateTime, nullable=True)
    pickup_notes = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=True)
    claimed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    claimed_at = Column(DateTime, nullable=True)
    claim_expires_at = Column(DateTime, nullable=True)
    assigned_driver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    retailer = relationship("Organization", back_populates="returns")
    pickup_partner = relationship("PickupPartner", back_populates="returns")
    creator = relationship("User", foreign_keys=[created_by_user_id])
    claimed_by = relationship("User", foreign_keys=[claimed_by_user_id])
    assigned_driver = relationship("User", foreign_keys=[assigned_driver_id])
    assessment = relationship("Assessment", back_populates="return_request", uselist=False, cascade="all, delete-orphan")
    cost_estimates = relationship("CostEstimate", back_populates="return_request", cascade="all, delete-orphan")
    decisions = relationship("RetailerDecision", back_populates="return_request", cascade="all, delete-orphan")
    processing_task = relationship("ProcessingTask", back_populates="return_request", uselist=False, cascade="all, delete-orphan")
    quality_check = relationship("QualityCheck", back_populates="return_request", uselist=False, cascade="all, delete-orphan")
    disposition = relationship("Disposition", back_populates="return_request", uselist=False, cascade="all, delete-orphan")
    status_history = relationship("ReturnStatusHistory", back_populates="return_request", cascade="all, delete-orphan", order_by="ReturnStatusHistory.created_at.asc()")


class DriverTaskRejection(Base):
    __tablename__ = "driver_task_rejections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(20), nullable=False)  # "REJECTED" or "RELEASED"
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    driver = relationship("User", foreign_keys=[driver_user_id])
    return_request = relationship("ReturnRequest", foreign_keys=[return_id])
