from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), unique=True, nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    physical_condition = Column(String(50), nullable=False)  # GOOD, LOW_DAMAGE, MEDIUM_DAMAGE, HIGH_DAMAGE
    screen_condition = Column(String(100), nullable=True)
    battery_health_pct = Column(Integer, nullable=True)
    functional_tests_passed = Column(Boolean, default=True, nullable=False)
    damage_notes = Column(Text, nullable=True)
    safety_concerns = Column(Text, nullable=True)
    assessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    return_request = relationship("ReturnRequest", back_populates="assessment")
    inspector = relationship("User", foreign_keys=[inspector_id])

class CostEstimate(Base):
    __tablename__ = "cost_estimates"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(String(50), ForeignKey("returns.id", ondelete="CASCADE"), nullable=False, index=True)
    option_type = Column(String(50), nullable=False)  # REFURBISH, REPAIR, RESALE_AS_IS, RETURN_TO_RETAILER, RECYCLE
    estimated_resale_value = Column(Numeric(10, 2), nullable=False, default=0.00)
    estimated_repair_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    estimated_transport_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    estimated_packaging_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    estimated_sanitization_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    estimated_nrv = Column(Numeric(10, 2), nullable=False, default=0.00)
    is_recommended = Column(Boolean, default=False, nullable=False)
    recommendation_reason = Column(Text, nullable=True)
    co2_saved_kg = Column(Numeric(10, 2), nullable=False, default=0.00)
    environmental_assumptions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    return_request = relationship("ReturnRequest", back_populates="cost_estimates")
