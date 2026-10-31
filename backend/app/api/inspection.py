from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import require_roles
from backend.app.database import get_db
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import User
from backend.app.schemas.execution import AssessmentCreate, ProcessingTaskCreate, QualityCheckCreate
from backend.app.schemas.return_request import ReturnDetailResponse
from backend.app.services.workflow_service import conduct_inspection, conduct_quality_check, execute_processing

router = APIRouter(prefix="/api/returns", tags=["Inspection and Processing"])

@router.post("/{return_id}/inspect", response_model=ReturnDetailResponse)
def inspect_return(
    return_id: str,
    data: AssessmentCreate,
    current_user: User = Depends(require_roles(["INSPECTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Conduct detailed physical & functional inspection, then generate recovery estimates."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    updated = conduct_inspection(
        db=db,
        return_obj=return_obj,
        physical_condition=data.physical_condition,
        screen_condition=data.screen_condition,
        battery_health_pct=data.battery_health_pct,
        functional_tests_passed=data.functional_tests_passed,
        damage_notes=data.damage_notes,
        safety_concerns=data.safety_concerns,
        actor=current_user
    )

    res = ReturnDetailResponse.model_validate(updated)
    res.organization_name = updated.retailer.name if updated.retailer else None
    return res

@router.post("/{return_id}/process", response_model=ReturnDetailResponse)
def process_return(
    return_id: str,
    data: ProcessingTaskCreate,
    current_user: User = Depends(require_roles(["INSPECTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Execute the authorized recovery action (refurbishment/repair) and log actual costs."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    updated = execute_processing(
        db=db,
        return_obj=return_obj,
        work_performed=data.work_performed,
        actual_repair_cost=data.actual_repair_cost,
        actual_packaging_cost=data.actual_packaging_cost,
        actual_labor_cost=data.actual_labor_cost,
        actual_transport_cost=data.actual_transport_cost,
        actor=current_user
    )

    res = ReturnDetailResponse.model_validate(updated)
    res.organization_name = updated.retailer.name if updated.retailer else None
    return res

@router.post("/{return_id}/qc", response_model=ReturnDetailResponse)
def quality_check_return(
    return_id: str,
    data: QualityCheckCreate,
    current_user: User = Depends(require_roles(["INSPECTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Perform post-processing quality inspection and verify data sanitization gate."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    updated = conduct_quality_check(
        db=db,
        return_obj=return_obj,
        functional_qc_passed=data.functional_qc_passed,
        cosmetic_grade=data.cosmetic_grade,
        sanitization_passed=data.sanitization_passed,
        sanitization_certificate=data.sanitization_certificate,
        sanitization_method=data.sanitization_method,
        qc_notes=data.qc_notes,
        actor=current_user
    )

    res = ReturnDetailResponse.model_validate(updated)
    res.organization_name = updated.retailer.name if updated.retailer else None
    return res
