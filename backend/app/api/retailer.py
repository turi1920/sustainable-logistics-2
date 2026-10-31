from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import require_roles, validate_retailer_access
from backend.app.database import get_db
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import User
from backend.app.schemas.execution import RetailerDecisionCreate
from backend.app.schemas.return_request import ReturnDetailResponse
from backend.app.services.workflow_service import approve_decision

router = APIRouter(prefix="/api/returns", tags=["Retailer Decisions"])

@router.post("/{return_id}/decide", response_model=ReturnDetailResponse)
def decide_return_option(
    return_id: str,
    data: RetailerDecisionCreate,
    current_user: User = Depends(require_roles(["RETAILER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Retailer authorization: Approve, reject, or select a recovery option.
    Enforces multi-tenant isolation: Retailer can ONLY decide on their own returns!
    """
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    # Multi-tenant isolation check
    validate_retailer_access(current_user, return_obj)

    updated = approve_decision(
        db=db,
        return_obj=return_obj,
        decision=data.decision,
        approved_option=data.approved_option,
        remarks=data.remarks,
        actor=current_user
    )

    res = ReturnDetailResponse.model_validate(updated)
    res.organization_name = updated.retailer.name if updated.retailer else None
    return res
