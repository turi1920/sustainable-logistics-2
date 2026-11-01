import random
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.dependencies import (
    get_current_user,
    require_roles,
    validate_partner_access,
    validate_retailer_access,
)
from backend.app.database import get_db
from backend.app.models.return_request import DriverTaskRejection, ReturnRequest
from backend.app.models.user import Organization, User
from backend.app.schemas.return_request import (
    DriverTaskActionRequest,
    ReturnCreate,
    ReturnDetailResponse,
    ReturnResponse,
    StatusHistoryItem,
)
from backend.app.services.audit_service import record_status_change

router = APIRouter(prefix="/api/returns", tags=["Returns"])

def populate_return_response(r: ReturnRequest, res):
    res.organization_name = r.retailer.name if r.retailer else None
    res.pickup_partner_name = r.pickup_partner.name if r.pickup_partner else None
    now = datetime.utcnow()
    is_active_claim = bool(r.claimed_by_user_id and r.claim_expires_at and r.claim_expires_at > now)
    res.is_claimed = is_active_claim
    if is_active_claim and r.claimed_by:
        res.claimed_by_username = r.claimed_by.username
        res.claimed_by_name = r.claimed_by.full_name
    elif not is_active_claim:
        res.claimed_by_user_id = None
        res.claimed_by_username = None
        res.claimed_by_name = None
    if r.assigned_driver:
        res.assigned_driver_id = r.assigned_driver_id
        res.assigned_driver_username = r.assigned_driver.username
        res.assigned_driver_name = r.assigned_driver.full_name
    else:
        res.assigned_driver_id = None
        res.assigned_driver_username = None
        res.assigned_driver_name = None
    return res

def generate_unique_return_id(db: Session, prefix: str = "RET") -> str:
    """Generate a unique primary key return ID (e.g. RET-YYYY-XXXX)."""
    year = datetime.utcnow().year
    for _ in range(100):
        rand_num = random.randint(1000, 9999)
        candidate = f"{prefix}-{year}-{rand_num}"
        if not db.query(ReturnRequest).filter(ReturnRequest.id == candidate).first():
            return candidate
    return f"{prefix}-{year}-{uuid.uuid4().hex[:6].upper()}"


@router.post("", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
def create_return(
    data: ReturnCreate,
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE"])),
    db: Session = Depends(get_db)
):
    """Register a new return case. Restricted to ADMIN and WAREHOUSE roles."""
    # Check if organization exists
    org = db.query(Organization).filter(Organization.id == data.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {data.organization_id} not found."
        )

    # Generate return ID if not provided (primary key auto-generation)
    if not data.return_id:
        return_id = generate_unique_return_id(db, prefix="RET")
    else:
        return_id = data.return_id.strip()

    # Check for duplicate return ID
    existing = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Return request with ID '{return_id}' already exists."
        )

    assigned_driver_id = data.assigned_driver_id
    pickup_partner_id = data.pickup_partner_id
    if assigned_driver_id and not pickup_partner_id:
        driver = db.query(User).filter(User.id == assigned_driver_id).first()
        if driver and driver.pickup_partner_id:
            pickup_partner_id = driver.pickup_partner_id

    return_obj = ReturnRequest(
        id=return_id,
        order_ref=data.order_ref,
        organization_id=data.organization_id,
        product_category=data.product_category,
        product_name=data.product_name,
        sku=data.sku,
        serial_expected=data.serial_expected,
        customer_pincode=data.customer_pincode,
        return_reason=data.return_reason,
        pickup_partner_id=pickup_partner_id,
        assigned_driver_id=assigned_driver_id,
        pickup_status="ASSIGNED" if (pickup_partner_id or assigned_driver_id) else "PENDING_ASSIGNMENT",
        status="RETURN_REQUESTED",
        created_by_user_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(return_obj)

    record_status_change(
        db=db,
        return_id=return_id,
        old_status=None,
        new_status="RETURN_REQUESTED",
        actor=current_user,
        action="REGISTER_RETURN",
        details=f"Registered return for {data.product_name} (SKU: {data.sku}). Order Ref: {data.order_ref}."
    )
    db.commit()
    db.refresh(return_obj)

    res = ReturnResponse.model_validate(return_obj)
    return populate_return_response(return_obj, res)

@router.get("", response_model=List[ReturnResponse])
def list_returns(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    assigned_to_me: Optional[bool] = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List returns with filtering and multi-tenant isolation.
    Retailers ONLY see returns for their own organization!
    """
    query = db.query(ReturnRequest)

    # Multi-tenant isolation enforcement
    if current_user.role == "RETAILER":
        query = query.filter(ReturnRequest.organization_id == current_user.organization_id)
    elif current_user.role == "PICKUP_PARTNER":
        if assigned_to_me:
            query = query.filter(ReturnRequest.assigned_driver_id == current_user.id)
        else:
            query = query.filter(
                or_(
                    ReturnRequest.pickup_partner_id == current_user.pickup_partner_id,
                    ReturnRequest.assigned_driver_id == current_user.id,
                )
            )

    if status_filter and status_filter != "ALL":
        query = query.filter(ReturnRequest.status == status_filter)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                ReturnRequest.id.ilike(s),
                ReturnRequest.order_ref.ilike(s),
                ReturnRequest.serial_expected.ilike(s),
                ReturnRequest.serial_received.ilike(s),
                ReturnRequest.product_name.ilike(s),
                ReturnRequest.sku.ilike(s)
            )
        )

    returns = query.order_by(ReturnRequest.created_at.desc()).all()
    results = []
    for r in returns:
        res = ReturnResponse.model_validate(r)
        results.append(populate_return_response(r, res))
    return results


@router.get("/generate-id")
def get_generated_return_id(
    prefix: str = "RET",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate the next unique Return Case ID (Primary Key)."""
    return {"return_id": generate_unique_return_id(db, prefix=prefix)}


@router.get("/marketplace", response_model=List[ReturnResponse])
def get_marketplace_returns(
    current_user: User = Depends(require_roles(["PICKUP_PARTNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Retrieve available returns in the Public Tasks Marketplace.
    Public across carriers: any driver can view and accept unassigned returns.
    Excludes:
    - Returns already accepted by any driver (assigned_driver_id IS NOT NULL)
    - Returns rejected or released by the current user
    - Returns that are already IN_TRANSIT, DELIVERED_TO_WAREHOUSE, or not in RETURN_REQUESTED status
    """
    excluded_ids_subquery = (
        db.query(DriverTaskRejection.return_id)
        .filter(DriverTaskRejection.driver_user_id == current_user.id)
    )

    query = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.status == "RETURN_REQUESTED")
        .filter(ReturnRequest.assigned_driver_id.is_(None))
        .filter(ReturnRequest.pickup_status.in_(["PENDING_ASSIGNMENT", "ASSIGNED", "RESCHEDULED"]))
        .filter(~ReturnRequest.id.in_(excluded_ids_subquery))
        .order_by(ReturnRequest.created_at.desc())
    )

    returns = query.all()
    results = []
    for r in returns:
        res = ReturnResponse.model_validate(r)
        results.append(populate_return_response(r, res))
    return results


@router.get("/{return_id}", response_model=ReturnDetailResponse)
def get_return_detail(
    return_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve full return case details.
    Enforces multi-tenant isolation: Retailer A cannot access Retailer B's return!
    """
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    # Multi-tenant isolation check
    validate_retailer_access(current_user, return_obj)
    validate_partner_access(current_user, return_obj)

    res = ReturnDetailResponse.model_validate(return_obj)
    return populate_return_response(return_obj, res)


@router.post("/{return_id}/accept", response_model=ReturnDetailResponse)
def accept_marketplace_task(
    return_id: str,
    current_user: User = Depends(require_roles(["PICKUP_PARTNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Driver accepts a return task from the public marketplace.
    Uses atomic row-level lock (with_for_update) to guarantee that one task
    is selected by one person only.
    """
    return_obj = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .with_for_update()
        .first()
    )
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    # Concurrency check: one task selected by one person only
    if return_obj.assigned_driver_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task has already been accepted by another driver."
        )

    if return_obj.status != "RETURN_REQUESTED" or return_obj.pickup_status in ["IN_TRANSIT", "DELIVERED_TO_WAREHOUSE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept return in status '{return_obj.status}' / pickup status '{return_obj.pickup_status}'."
        )

    # Assign task to this driver and their partner carrier
    return_obj.assigned_driver_id = current_user.id
    if current_user.pickup_partner_id:
        return_obj.pickup_partner_id = current_user.pickup_partner_id
    return_obj.pickup_status = "ASSIGNED"
    return_obj.updated_at = datetime.utcnow()

    record_status_change(
        db=db,
        return_id=return_id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="DRIVER_ACCEPTED_TASK",
        details=f"Driver {current_user.full_name} ({current_user.username}) accepted task from public marketplace."
    )
    db.commit()
    db.refresh(return_obj)

    res = ReturnDetailResponse.model_validate(return_obj)
    return populate_return_response(return_obj, res)


@router.post("/{return_id}/reject")
def reject_marketplace_task(
    return_id: str,
    data: Optional[DriverTaskActionRequest] = None,
    current_user: User = Depends(require_roles(["PICKUP_PARTNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Driver rejects/skips a task from the public marketplace.
    Does NOT cancel the return. It only hides it from this driver's feed,
    keeping it available for other drivers.
    """
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    reason = data.reason if data else None

    # Record rejection for this driver
    rejection = DriverTaskRejection(
        driver_user_id=current_user.id,
        return_id=return_id,
        action_type="REJECTED",
        reason=reason,
        created_at=datetime.utcnow()
    )
    db.add(rejection)

    record_status_change(
        db=db,
        return_id=return_id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="DRIVER_REJECTED_TASK",
        details=f"Driver {current_user.full_name} skipped/rejected task in marketplace. Reason: {reason or 'No reason provided'}."
    )
    db.commit()

    return {
        "message": f"Task '{return_id}' dismissed from your marketplace feed.",
        "return_id": return_id,
        "action": "REJECTED"
    }


@router.post("/{return_id}/release")
def release_driver_task(
    return_id: str,
    data: Optional[DriverTaskActionRequest] = None,
    current_user: User = Depends(require_roles(["PICKUP_PARTNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Driver drops/releases an accepted task back to the marketplace.
    Once released:
    - It goes back to the public marketplace for other drivers.
    - It will never appear again to the releasing driver.
    """
    return_obj = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .with_for_update()
        .first()
    )
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    # Permission check: must be assigned to this driver or their carrier (or admin)
    is_assigned_to_driver = return_obj.assigned_driver_id == current_user.id
    is_assigned_to_carrier = (
        return_obj.assigned_driver_id is None
        and current_user.pickup_partner_id is not None
        and return_obj.pickup_partner_id == current_user.pickup_partner_id
    )
    if current_user.role != "ADMIN" and not (is_assigned_to_driver or is_assigned_to_carrier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only release tasks assigned to you or your carrier."
        )

    if return_obj.pickup_status in ["IN_TRANSIT", "DELIVERED_TO_WAREHOUSE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot release a task that has already been collected or delivered."
        )

    reason = data.reason if data else None

    # Unassign driver and carrier so it returns to public marketplace
    return_obj.assigned_driver_id = None
    return_obj.pickup_partner_id = None
    return_obj.pickup_status = "PENDING_ASSIGNMENT"
    return_obj.updated_at = datetime.utcnow()

    # Record self-exclusion so it never appears again to this driver
    rejection = DriverTaskRejection(
        driver_user_id=current_user.id,
        return_id=return_id,
        action_type="RELEASED",
        reason=reason,
        created_at=datetime.utcnow()
    )
    db.add(rejection)

    record_status_change(
        db=db,
        return_id=return_id,
        old_status=return_obj.status,
        new_status=return_obj.status,
        actor=current_user,
        action="DRIVER_RELEASED_TASK",
        details=f"Driver {current_user.full_name} released task back to marketplace. Reason: {reason or 'Shift end / route change'}."
    )
    db.commit()

    return {
        "message": f"Task '{return_id}' released back to marketplace.",
        "return_id": return_id,
        "action": "RELEASED"
    }


@router.get("/{return_id}/journey", response_model=List[StatusHistoryItem])
def get_return_journey(
    return_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the complete audit trail and status transition history."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    # Multi-tenant isolation check
    validate_retailer_access(current_user, return_obj)
    validate_partner_access(current_user, return_obj)

    history = return_obj.status_history
    return [StatusHistoryItem.model_validate(h) for h in history]
