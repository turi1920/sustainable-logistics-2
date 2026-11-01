from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ReturnCreate(BaseModel):
    return_id: Optional[str] = None
    order_ref: Optional[str] = None
    organization_id: int
    product_category: str = "Smartphone"
    product_name: str
    sku: str
    serial_expected: Optional[str] = None
    customer_pincode: Optional[str] = None
    return_reason: Optional[str] = None
    pickup_partner_id: Optional[int] = None
    assigned_driver_id: Optional[int] = None

class PickupAssignment(BaseModel):
    pickup_partner_id: Optional[int] = None
    assigned_driver_id: Optional[int] = None
    scheduled_date: Optional[datetime] = None
    notes: Optional[str] = None

class ReturnReceive(BaseModel):
    serial_received: str
    storage_location: str
    package_condition: str = "Good"

class StatusHistoryItem(BaseModel):
    id: int
    return_id: str
    old_status: Optional[str] = None
    new_status: str
    actor_username: str
    actor_role: str
    action: str
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CostEstimateItem(BaseModel):
    id: int
    option_type: str
    estimated_resale_value: Decimal
    estimated_repair_cost: Decimal
    estimated_transport_cost: Decimal
    estimated_packaging_cost: Decimal
    estimated_sanitization_cost: Decimal
    estimated_nrv: Decimal
    is_recommended: bool
    recommendation_reason: Optional[str] = None
    co2_saved_kg: Decimal
    environmental_assumptions: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AssessmentItem(BaseModel):
    id: int
    physical_condition: str
    screen_condition: Optional[str] = None
    battery_health_pct: Optional[int] = None
    functional_tests_passed: bool
    damage_notes: Optional[str] = None
    safety_concerns: Optional[str] = None
    assessed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DecisionItem(BaseModel):
    id: int
    decision: str
    approved_option: str
    remarks: Optional[str] = None
    decided_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProcessingItem(BaseModel):
    id: int
    work_performed: str
    actual_repair_cost: Decimal
    actual_packaging_cost: Decimal
    actual_labor_cost: Decimal
    actual_transport_cost: Decimal
    total_actual_cost: Decimal
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class QualityCheckItem(BaseModel):
    id: int
    functional_qc_passed: bool
    cosmetic_grade: str
    sanitization_passed: bool
    sanitization_certificate: Optional[str] = None
    sanitization_method: Optional[str] = None
    qc_notes: Optional[str] = None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DispositionItem(BaseModel):
    id: int
    disposition_type: str
    inventory_location: Optional[str] = None
    realized_resale_value: Decimal
    notes: Optional[str] = None
    disposed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReturnResponse(BaseModel):
    id: str
    order_ref: Optional[str] = None
    organization_id: int
    organization_name: Optional[str] = None
    product_category: str
    product_name: str
    sku: str
    serial_expected: Optional[str] = None
    serial_received: Optional[str] = None
    customer_pincode: Optional[str] = None
    return_reason: Optional[str] = None
    status: str
    storage_location: Optional[str] = None
    package_condition: Optional[str] = None
    pickup_partner_id: Optional[int] = None
    pickup_partner_name: Optional[str] = None
    pickup_status: str = "PENDING_ASSIGNMENT"
    pickup_scheduled_date: Optional[datetime] = None
    pickup_notes: Optional[str] = None
    claimed_by_user_id: Optional[int] = None
    claimed_by_username: Optional[str] = None
    claimed_by_name: Optional[str] = None
    claimed_at: Optional[datetime] = None
    claim_expires_at: Optional[datetime] = None
    is_claimed: bool = False
    assigned_driver_id: Optional[int] = None
    assigned_driver_name: Optional[str] = None
    assigned_driver_username: Optional[str] = None
    received_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DriverTaskActionRequest(BaseModel):
    reason: Optional[str] = None

class ReturnDetailResponse(ReturnResponse):
    assessment: Optional[AssessmentItem] = None
    cost_estimates: List[CostEstimateItem] = []
    decisions: List[DecisionItem] = []
    processing_task: Optional[ProcessingItem] = None
    quality_check: Optional[QualityCheckItem] = None
    disposition: Optional[DispositionItem] = None
    status_history: List[StatusHistoryItem] = []
