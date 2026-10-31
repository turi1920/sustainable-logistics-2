import random
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user, require_roles, validate_retailer_access
from backend.app.database import get_db
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import Organization, User
from backend.app.schemas.return_request import ReturnCreate, ReturnDetailResponse, ReturnResponse, StatusHistoryItem
from backend.app.services.audit_service import record_status_change

router = APIRouter(prefix="/api/returns", tags=["Returns"])

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

    # Generate return ID if not provided
    if not data.return_id:
        year = datetime.utcnow().year
        rand_num = random.randint(1000, 9999)
        prefix = "RET"
        if data.product_category.lower() == "smartphone":
            prefix = "RET-SMP"
        return_id = f"{prefix}-{year}-{rand_num}"
    else:
        return_id = data.return_id

    # Check for duplicate return ID
    existing = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Return request with ID '{return_id}' already exists."
        )

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
    res.organization_name = org.name
    return res

@router.get("", response_model=List[ReturnResponse])
def list_returns(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
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
        res.organization_name = r.retailer.name if r.retailer else None
        results.append(res)
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

    res = ReturnDetailResponse.model_validate(return_obj)
    res.organization_name = return_obj.retailer.name if return_obj.retailer else None
    return res

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

    history = return_obj.status_history
    return [StatusHistoryItem.model_validate(h) for h in history]
