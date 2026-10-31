from typing import Optional

from pydantic import BaseModel, Field


class AssessmentCreate(BaseModel):
    physical_condition: str = Field(..., description="GOOD, LOW_DAMAGE, MEDIUM_DAMAGE, HIGH_DAMAGE")
    screen_condition: Optional[str] = "Minor scratches"
    battery_health_pct: Optional[int] = Field(85, ge=0, le=100)
    functional_tests_passed: bool = True
    damage_notes: Optional[str] = None
    safety_concerns: Optional[str] = None

class RetailerDecisionCreate(BaseModel):
    decision: str = Field("APPROVED", description="APPROVED, REJECTED, CHANGED")
    approved_option: str = Field(..., description="REFURBISH, REPAIR, RESALE_AS_IS, RETURN_TO_RETAILER, RECYCLE")
    remarks: Optional[str] = None

class ProcessingTaskCreate(BaseModel):
    work_performed: str
    actual_repair_cost: float = 0.0
    actual_packaging_cost: float = 0.0
    actual_labor_cost: float = 0.0
    actual_transport_cost: float = 0.0

class QualityCheckCreate(BaseModel):
    functional_qc_passed: bool = True
    cosmetic_grade: str = "GRADE_A"  # GRADE_A, GRADE_B, GRADE_C
    sanitization_passed: bool = True
    sanitization_certificate: Optional[str] = "CERT-NIST-800-88"
    sanitization_method: Optional[str] = "Cryptographic Erasure NIST SP 800-88 Rev 1"
    qc_notes: Optional[str] = None

class DispositionCreate(BaseModel):
    disposition_type: str = Field(..., description="RESTOCKED or RETURNED_TO_RETAILER")
    inventory_location: Optional[str] = "MAIN_WAREHOUSE_SHELF_A"
    realized_resale_value: float = 0.0
    notes: Optional[str] = None
