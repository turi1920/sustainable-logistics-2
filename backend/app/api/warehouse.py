from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import require_roles
from backend.app.database import get_db
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import User
from backend.app.schemas.execution import DispositionCreate
from backend.app.schemas.return_request import ReturnReceive, ReturnResponse
from backend.app.services.workflow_service import finalize_disposition, receive_return

router = APIRouter(prefix="/api/returns", tags=["Warehouse Operations"])

@router.post("/{return_id}/receive", response_model=ReturnResponse)
def warehouse_receive(
    return_id: str,
    data: ReturnReceive,
    current_user: User = Depends(require_roles(["WAREHOUSE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Confirm receipt of returned product at the warehouse facility."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    updated = receive_return(
        db=db,
        return_obj=return_obj,
        serial_received=data.serial_received,
        storage_location=data.storage_location,
        package_condition=data.package_condition,
        actor=current_user
    )

    res = ReturnResponse.model_validate(updated)
    res.organization_name = updated.retailer.name if updated.retailer else None
    return res

@router.post("/{return_id}/restock", response_model=ReturnResponse)
def warehouse_restock(
    return_id: str,
    data: DispositionCreate,
    current_user: User = Depends(require_roles(["WAREHOUSE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Finalize disposition: Restock into resale inventory or record return to retailer."""
    return_obj = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return case '{return_id}' not found."
        )

    updated = finalize_disposition(
        db=db,
        return_obj=return_obj,
        disposition_type=data.disposition_type,
        inventory_location=data.inventory_location,
        realized_resale_value=data.realized_resale_value,
        notes=data.notes,
        actor=current_user
    )

    res = ReturnResponse.model_validate(updated)
    res.organization_name = updated.retailer.name if updated.retailer else None
    return res
