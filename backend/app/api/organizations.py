from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models.user import Organization

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])

class OrgResponse(BaseModel):
    id: int
    name: str
    org_type: str
    contact_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[OrgResponse])
def list_organizations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    orgs = db.query(Organization).order_by(Organization.id.asc()).all()
    return orgs
