from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from backend.app.database import Base


class PickupPartner(Base):
    __tablename__ = "pickup_partners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    service_regions = Column(String(255), nullable=True)
    fleet_type = Column(String(100), nullable=False, default="Electric Van (Zero-Emission)")
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    returns = relationship("ReturnRequest", back_populates="pickup_partner")
    users = relationship("User", back_populates="pickup_partner")
