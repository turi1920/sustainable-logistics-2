from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user, require_roles
from backend.app.database import get_db
from backend.app.models.pickup_partner import PickupPartner
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import User
from backend.app.schemas.pickup_partner import PickupPartnerCreate, PickupPartnerResponse
from backend.app.schemas.return_request import PickupAssignment, ReturnDetailResponse
from backend.app.services.audit_service import record_status_change

router = APIRouter(tags=["Pickup Partners & Field Logistics"])

class ConfirmPickupRequest(BaseModel):
    picked_up_notes: Optional[str] = "Customer package collected and secured in logistics vehicle."

class DeliverWarehouseRequest(BaseModel):
    delivery_notes: Optional[str] = "Arrived at central warehouse receiving dock and handed over to intake team."

class FailPickupRequest(BaseModel):
    failure_reason: str
    failure_notes: Optional[str] = None
    reschedule_date: Optional[datetime] = None

class ReschedulePickupRequest(BaseModel):
    reschedule_date: datetime
    reschedule_notes: Optional[str] = None

@router.get("/api/pickup-partners", response_model=List[PickupPartnerResponse])
def list_pickup_partners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all registered pickup partners and 3PL carriers."""
    partners = db.query(PickupPartner).order_by(PickupPartner.id.asc()).all()
    return partners

@router.post("/api/pickup-partners", response_model=PickupPartnerResponse, status_code=status.HTTP_201_CREATED)
def create_pickup_partner(
    data: PickupPartnerCreate,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Register a new pickup partner/carrier. Restricted to Platform Admin."""
    existing = db.query(PickupPartner).filter(PickupPartner.name == data.name.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pickup partner with name '{data.name}' already exists."
        )

    partner = PickupPartner(
        name=data.name.strip(),
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        service_regions=data.service_regions,
        fleet_type=data.fleet_type,
        active=data.active,
        created_at=datetime.utcnow()
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner

@router.delete("/api/pickup-partners/{partner_id}", status_code=status.HTTP_200_OK)
def delete_pickup_partner(
    partner_id: int,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Remove a pickup partner. Restricted to Platform Admin."""
    partner = db.query(PickupPartner).filter(PickupPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pickup partner with ID {partner_id} not found."
        )

    name = partner.name
    db.delete(partner)
    db.commit()
    return {"status": "success", "message": f"Pickup partner '{name}' removed from database successfully."}

@router.post("/api/returns/{return_id}/assign-pickup", response_model=ReturnDetailResponse)
def assign_pickup_partner(
    return_id: str,
    data: PickupAssignment,
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE"])),
    db: Session = Depends(get_db)
):
    """Assign a pickup driver or partner to collect a return case from the customer."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    driver = None
    if data.assigned_driver_id:
        driver = db.query(User).filter(User.id == data.assigned_driver_id).first()
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Driver user with ID {data.assigned_driver_id} not found."
            )
        return_obj.assigned_driver_id = driver.id
        if driver.pickup_partner_id and not data.pickup_partner_id:
            return_obj.pickup_partner_id = driver.pickup_partner_id

    partner = None
    if data.pickup_partner_id:
        partner = db.query(PickupPartner).filter(PickupPartner.id == data.pickup_partner_id).first()
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pickup partner with ID {data.pickup_partner_id} not found."
            )
        return_obj.pickup_partner_id = partner.id

    if not data.assigned_driver_id and not data.pickup_partner_id:
        # Unassigned / dispatch to marketplace
        return_obj.assigned_driver_id = None
        return_obj.pickup_partner_id = None
        return_obj.pickup_status = "PENDING_ASSIGNMENT"
    else:
        return_obj.pickup_status = "ASSIGNED"

    return_obj.pickup_scheduled_date = data.scheduled_date or datetime.utcnow()
    return_obj.pickup_notes = data.notes

    driver_label = driver.full_name if driver else (return_obj.assigned_driver.full_name if return_obj.assigned_driver else "Marketplace Pool")
    carrier_label = partner.name if partner else (return_obj.pickup_partner.name if return_obj.pickup_partner else "Independent / Open")

    record_status_change(
        db=db,
        return_id=return_obj.id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="ASSIGN_PICKUP_PARTNER",
        details=f"Assigned pickup driver: {driver_label} (Carrier: {carrier_label}). Notes: {data.notes or 'None'}."
    )
    db.commit()
    db.refresh(return_obj)

    res = ReturnDetailResponse.model_validate(return_obj)
    res.organization_name = return_obj.retailer.name if return_obj.retailer else None
    res.pickup_partner_name = return_obj.pickup_partner.name if return_obj.pickup_partner else None
    if return_obj.assigned_driver:
        res.assigned_driver_id = return_obj.assigned_driver_id
        res.assigned_driver_name = return_obj.assigned_driver.full_name
        res.assigned_driver_username = return_obj.assigned_driver.username
    return res

@router.post("/api/returns/{return_id}/confirm-pickup", response_model=ReturnDetailResponse)
def confirm_pickup_collection(
    return_id: str,
    data: ConfirmPickupRequest,
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE", "PICKUP_PARTNER"])),
    db: Session = Depends(get_db)
):
    """Confirm physical pickup/collection from the customer by the assigned partner."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    if current_user.role == "PICKUP_PARTNER":
        if return_obj.pickup_partner_id != current_user.pickup_partner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to confirm collection for another carrier's shipment."
            )

    partner_name = return_obj.pickup_partner.name if return_obj.pickup_partner else "Pickup Carrier"
    return_obj.pickup_status = "IN_TRANSIT"

    record_status_change(
        db=db,
        return_id=return_obj.id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="CONFIRM_PICKUP_COLLECTION",
        details=f"Collected by {partner_name}. Package now in-transit to warehouse. Notes: {data.picked_up_notes}."
    )
    db.commit()
    db.refresh(return_obj)

    res = ReturnDetailResponse.model_validate(return_obj)
    res.organization_name = return_obj.retailer.name if return_obj.retailer else None
    res.pickup_partner_name = partner_name
    return res

@router.post("/api/returns/{return_id}/deliver-warehouse", response_model=ReturnDetailResponse)
def deliver_pickup_to_warehouse(
    return_id: str,
    data: DeliverWarehouseRequest,
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE", "PICKUP_PARTNER"])),
    db: Session = Depends(get_db)
):
    """Confirm delivery and handover to warehouse receiving dock by the pickup driver."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    if current_user.role == "PICKUP_PARTNER":
        if return_obj.pickup_partner_id != current_user.pickup_partner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to deliver another carrier's shipment."
            )

    partner_name = return_obj.pickup_partner.name if return_obj.pickup_partner else "Pickup Carrier"
    return_obj.pickup_status = "DELIVERED_TO_WAREHOUSE"

    record_status_change(
        db=db,
        return_id=return_obj.id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="DELIVER_TO_WAREHOUSE_DOCK",
        details=f"Handed over to central warehouse dock by {partner_name}. Notes: {data.delivery_notes}."
    )
    db.commit()
    db.refresh(return_obj)

    res = ReturnDetailResponse.model_validate(return_obj)
    res.organization_name = return_obj.retailer.name if return_obj.retailer else None
    res.pickup_partner_name = partner_name
    return res

@router.post("/api/returns/{return_id}/fail-pickup", response_model=ReturnDetailResponse)
def fail_pickup_collection(
    return_id: str,
    data: FailPickupRequest,
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE", "PICKUP_PARTNER"])),
    db: Session = Depends(get_db)
):
    """Record a failed doorstep pickup attempt with categorized exception reason and notes."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    if current_user.role == "PICKUP_PARTNER":
        if return_obj.pickup_partner_id != current_user.pickup_partner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to report failure for another carrier's shipment."
            )

    if return_obj.status != "RETURN_REQUESTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot report pickup failure for return '{return_id}' because it is already in '{return_obj.status}' status."
        )

    partner_name = return_obj.pickup_partner.name if return_obj.pickup_partner else "Pickup Carrier"

    if data.reschedule_date:
        return_obj.pickup_status = "RESCHEDULED"
        return_obj.pickup_scheduled_date = data.reschedule_date
        status_note = f"Pickup attempt failed ({data.failure_reason}). Rescheduled for {data.reschedule_date.strftime('%Y-%m-%d %H:%M')}."
    else:
        return_obj.pickup_status = "PICKUP_FAILED"
        status_note = f"Pickup attempt failed ({data.failure_reason})."

    full_notes = f"{status_note} Notes: {data.failure_notes or 'No additional notes'}."
    return_obj.pickup_notes = full_notes

    record_status_change(
        db=db,
        return_id=return_obj.id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="RECORD_PICKUP_FAILURE",
        details=f"Doorstep collection attempt failed by {partner_name}. Reason: {data.failure_reason}. Status: {return_obj.pickup_status}. Notes: {data.failure_notes or 'None'}."
    )
    db.commit()
    db.refresh(return_obj)

    res = ReturnDetailResponse.model_validate(return_obj)
    res.organization_name = return_obj.retailer.name if return_obj.retailer else None
    res.pickup_partner_name = partner_name
    return res

@router.post("/api/returns/{return_id}/reschedule-pickup", response_model=ReturnDetailResponse)
def reschedule_pickup(
    return_id: str,
    data: ReschedulePickupRequest,
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE", "PICKUP_PARTNER"])),
    db: Session = Depends(get_db)
):
    """Reschedule a failed or pending doorstep pickup with a new scheduled collection date."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    if current_user.role == "PICKUP_PARTNER":
        if return_obj.pickup_partner_id != current_user.pickup_partner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to reschedule another carrier's shipment."
            )

    if return_obj.status != "RETURN_REQUESTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule pickup for return '{return_id}' because it is already in '{return_obj.status}' status."
        )

    partner_name = return_obj.pickup_partner.name if return_obj.pickup_partner else "Pickup Carrier"
    return_obj.pickup_status = "RESCHEDULED"
    return_obj.pickup_scheduled_date = data.reschedule_date
    resched_notes = f"Rescheduled for {data.reschedule_date.strftime('%Y-%m-%d %H:%M')}. Notes: {data.reschedule_notes or 'None'}."
    return_obj.pickup_notes = resched_notes

    record_status_change(
        db=db,
        return_id=return_obj.id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="RESCHEDULE_PICKUP",
        details=f"Pickup rescheduled for {data.reschedule_date.strftime('%Y-%m-%d %H:%M')} with {partner_name}. Notes: {data.reschedule_notes or 'None'}."
    )
    db.commit()
    db.refresh(return_obj)

    res = ReturnDetailResponse.model_validate(return_obj)
    res.organization_name = return_obj.retailer.name if return_obj.retailer else None
    res.pickup_partner_name = partner_name
    return res
