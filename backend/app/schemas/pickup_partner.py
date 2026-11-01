from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PickupPartnerCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    service_regions: Optional[str] = "Metro Hubs, Nationwide"
    fleet_type: str = "Electric Van (Zero-Emission)"
    active: bool = True

class PickupPartnerResponse(BaseModel):
    id: int
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    service_regions: Optional[str] = None
    fleet_type: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
