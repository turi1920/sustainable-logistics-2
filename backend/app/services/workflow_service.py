from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.assessment import Assessment, CostEstimate
from backend.app.models.decision import RetailerDecision
from backend.app.models.execution import Disposition, ProcessingTask, QualityCheck
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import User
from backend.app.services.audit_service import record_status_change
from backend.app.services.recovery_policy_service import generate_recovery_options

# Valid State Progression Map
ALLOWED_TRANSITIONS = {
    "RETURN_REQUESTED": ["RECEIVED"],
    "RECEIVED": ["AWAITING_APPROVAL", "INSPECTED"],
    "AWAITING_APPROVAL": ["APPROVED", "REJECTED"],
    "APPROVED": ["PROCESSING_COMPLETED"],
    "PROCESSING_COMPLETED": ["QC_PASSED"],
    "QC_PASSED": ["RESTOCKED", "RETURNED_TO_RETAILER", "COMPLETED"],
    "RESTOCKED": ["COMPLETED"],
    "RETURNED_TO_RETAILER": ["COMPLETED"],
    "REJECTED": ["RETURNED_TO_RETAILER", "RECYCLED", "COMPLETED"],
}

def validate_transition(current_status: str, target_status: str):
    valid_targets = ALLOWED_TRANSITIONS.get(current_status, [])
    if target_status not in valid_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow transition: cannot move from '{current_status}' to '{target_status}'. Expected one of {valid_targets}."
        )

def receive_return(
    db: Session,
    return_obj: ReturnRequest,
    serial_received: str,
    storage_location: str,
    package_condition: str,
    actor: User
) -> ReturnRequest:
    validate_transition(return_obj.status, "RECEIVED")
    old_status = return_obj.status
    return_obj.status = "RECEIVED"
    return_obj.serial_received = serial_received
    return_obj.storage_location = storage_location
    return_obj.package_condition = package_condition
    return_obj.received_at = datetime.utcnow()

    details = f"Received at location {storage_location}. Package condition: {package_condition}. Serial verified: {serial_received}."
    record_status_change(db, return_obj.id, old_status, "RECEIVED", actor, "CONFIRM_WAREHOUSE_RECEIPT", details)
    db.commit()
    db.refresh(return_obj)
    return return_obj

def conduct_inspection(
    db: Session,
    return_obj: ReturnRequest,
    physical_condition: str,
    screen_condition: Optional[str],
    battery_health_pct: Optional[int],
    functional_tests_passed: bool,
    damage_notes: Optional[str],
    safety_concerns: Optional[str],
    actor: User
) -> ReturnRequest:
    validate_transition(return_obj.status, "AWAITING_APPROVAL")
    old_status = return_obj.status

    # Create or update assessment
    assessment = Assessment(
        return_id=return_obj.id,
        inspector_id=actor.id,
        physical_condition=physical_condition,
        screen_condition=screen_condition,
        battery_health_pct=battery_health_pct,
        functional_tests_passed=functional_tests_passed,
        damage_notes=damage_notes,
        safety_concerns=safety_concerns,
        assessed_at=datetime.utcnow()
    )
    db.add(assessment)

    # Generate and store cost estimates
    base_resale = Decimal("400.00") if return_obj.product_category == "Smartphone" else Decimal("150.00")
    estimates_data = generate_recovery_options(
        product_category=return_obj.product_category,
        base_resale_value=base_resale,
        physical_condition=physical_condition,
        battery_health=battery_health_pct or 85,
        functional_passed=functional_tests_passed
    )

    # Clear prior estimates if any
    db.query(CostEstimate).filter(CostEstimate.return_id == return_obj.id).delete()

    for item in estimates_data:
        ce = CostEstimate(
            return_id=return_obj.id,
            option_type=item["option_type"],
            estimated_resale_value=item["estimated_resale_value"],
            estimated_repair_cost=item["estimated_repair_cost"],
            estimated_transport_cost=item["estimated_transport_cost"],
            estimated_packaging_cost=item["estimated_packaging_cost"],
            estimated_sanitization_cost=item["estimated_sanitization_cost"],
            estimated_nrv=item["estimated_nrv"],
            is_recommended=item["is_recommended"],
            recommendation_reason=item["recommendation_reason"],
            co2_saved_kg=item["co2_saved_kg"],
            environmental_assumptions=item["environmental_assumptions"],
            created_at=datetime.utcnow()
        )
        db.add(ce)

    return_obj.status = "AWAITING_APPROVAL"
    details = f"Inspection completed. Condition: {physical_condition}. Battery: {battery_health_pct}%. Functional: {functional_tests_passed}. Options generated."
    record_status_change(db, return_obj.id, old_status, "AWAITING_APPROVAL", actor, "COMPLETE_INSPECTION", details)
    db.commit()
    db.refresh(return_obj)
    return return_obj

def approve_decision(
    db: Session,
    return_obj: ReturnRequest,
    decision: str,
    approved_option: str,
    remarks: Optional[str],
    actor: User
) -> ReturnRequest:
    validate_transition(return_obj.status, decision)
    old_status = return_obj.status

    dec = RetailerDecision(
        return_id=return_obj.id,
        decided_by_user_id=actor.id,
        decision=decision,
        approved_option=approved_option,
        remarks=remarks,
        decided_at=datetime.utcnow()
    )
    db.add(dec)

    return_obj.status = decision
    details = f"Retailer decision: {decision} for option '{approved_option}'. Remarks: {remarks or 'None'}."
    record_status_change(db, return_obj.id, old_status, decision, actor, "RECORD_RETAILER_DECISION", details)
    db.commit()
    db.refresh(return_obj)
    return return_obj

def execute_processing(
    db: Session,
    return_obj: ReturnRequest,
    work_performed: str,
    actual_repair_cost: float,
    actual_packaging_cost: float,
    actual_labor_cost: float,
    actual_transport_cost: float,
    actor: User
) -> ReturnRequest:
    validate_transition(return_obj.status, "PROCESSING_COMPLETED")
    old_status = return_obj.status

    total_actual = Decimal(str(actual_repair_cost + actual_packaging_cost + actual_labor_cost + actual_transport_cost))

    task = ProcessingTask(
        return_id=return_obj.id,
        performed_by_user_id=actor.id,
        work_performed=work_performed,
        actual_repair_cost=Decimal(str(actual_repair_cost)),
        actual_packaging_cost=Decimal(str(actual_packaging_cost)),
        actual_labor_cost=Decimal(str(actual_labor_cost)),
        actual_transport_cost=Decimal(str(actual_transport_cost)),
        total_actual_cost=total_actual,
        completed_at=datetime.utcnow()
    )
    db.add(task)

    return_obj.status = "PROCESSING_COMPLETED"
    details = f"Processing finished: '{work_performed}'. Total actual cost: ${total_actual:.2f}."
    record_status_change(db, return_obj.id, old_status, "PROCESSING_COMPLETED", actor, "COMPLETE_PROCESSING", details)
    db.commit()
    db.refresh(return_obj)
    return return_obj

def conduct_quality_check(
    db: Session,
    return_obj: ReturnRequest,
    functional_qc_passed: bool,
    cosmetic_grade: str,
    sanitization_passed: bool,
    sanitization_certificate: Optional[str],
    sanitization_method: Optional[str],
    qc_notes: Optional[str],
    actor: User
) -> ReturnRequest:
    validate_transition(return_obj.status, "QC_PASSED")

    # Requirement 11: Data Sanitization and Resale Gate
    # A device with failed or unverifiable sanitization must not be released for resale!
    if not sanitization_passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sanitization Gate Failed: Device data sanitization must pass and be verified before quality check can be certified."
        )

    old_status = return_obj.status

    qc = QualityCheck(
        return_id=return_obj.id,
        checked_by_user_id=actor.id,
        functional_qc_passed=functional_qc_passed,
        cosmetic_grade=cosmetic_grade,
        sanitization_passed=sanitization_passed,
        sanitization_certificate=sanitization_certificate,
        sanitization_method=sanitization_method,
        qc_notes=qc_notes,
        checked_at=datetime.utcnow()
    )
    db.add(qc)

    return_obj.status = "QC_PASSED"
    details = f"Quality check passed. Grade: {cosmetic_grade}. Data Sanitization Certified: {sanitization_certificate} via {sanitization_method}."
    record_status_change(db, return_obj.id, old_status, "QC_PASSED", actor, "COMPLETE_QUALITY_CHECK", details)
    db.commit()
    db.refresh(return_obj)
    return return_obj

def finalize_disposition(
    db: Session,
    return_obj: ReturnRequest,
    disposition_type: str,  # RESTOCKED or RETURNED_TO_RETAILER
    inventory_location: Optional[str],
    realized_resale_value: float,
    notes: Optional[str],
    actor: User
) -> ReturnRequest:
    target_status = "RESTOCKED" if disposition_type == "RESTOCKED" else "RETURNED_TO_RETAILER"
    validate_transition(return_obj.status, target_status)
    old_status = return_obj.status

    disp = Disposition(
        return_id=return_obj.id,
        handled_by_user_id=actor.id,
        disposition_type=target_status,
        inventory_location=inventory_location,
        realized_resale_value=Decimal(str(realized_resale_value)),
        notes=notes,
        disposed_at=datetime.utcnow()
    )
    db.add(disp)

    return_obj.status = "COMPLETED"
    details = f"Disposition completed: {target_status}. Location: {inventory_location}. Realized value: ${realized_resale_value:.2f}. Notes: {notes or 'None'}."
    record_status_change(db, return_obj.id, old_status, "COMPLETED", actor, f"DISPOSITION_{target_status}", details)
    db.commit()
    db.refresh(return_obj)
    return return_obj
