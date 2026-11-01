from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.dependencies import require_roles
from backend.app.core.security import hash_password
from backend.app.database import get_db
from backend.app.models.pickup_partner import PickupPartner
from backend.app.models.user import Organization, User
from backend.app.schemas.auth import UserCreate, UserResponse

router = APIRouter(prefix="/api/users", tags=["User Management"])

@router.get("", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """List all registered users across the platform. Restricted to Platform Admin."""
    users = db.query(User).order_by(User.id.asc()).all()
    results = []
    for u in users:
        res = UserResponse.model_validate(u)
        res.organization_name = u.organization.name if u.organization else None
        res.pickup_partner_name = u.pickup_partner.name if u.pickup_partner else None
        results.append(res)
    return results

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Add a new user with secure password hashing and role assignment. Restricted to Platform Admin."""
    # Check if username or email exists
    existing = db.query(User).filter(
        or_(
            User.username == data.username.strip(),
            User.email == data.email.strip().lower()
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username '{data.username}' or email '{data.email}' already exists."
        )

    # Validate organization if role is RETAILER
    if data.role == "RETAILER" and not data.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization must be assigned for users with role 'RETAILER'."
        )

    partner_id = data.pickup_partner_id
    if partner_id:
        partner = db.query(PickupPartner).filter(PickupPartner.id == partner_id).first()
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pickup partner with ID {partner_id} not found."
            )

    org_id = data.organization_id
    if not org_id and data.role != "RETAILER":
        platform_org = db.query(Organization).filter(Organization.org_type == "PLATFORM").first()
        if platform_org:
            org_id = platform_org.id

    if org_id:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with ID {org_id} not found."
            )

    new_user = User(
        username=data.username.strip(),
        email=data.email.strip().lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
        organization_id=org_id,
        pickup_partner_id=partner_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    res = UserResponse.model_validate(new_user)
    res.organization_name = new_user.organization.name if new_user.organization else None
    res.pickup_partner_name = new_user.pickup_partner.name if new_user.pickup_partner else None
    return res

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Remove an existing user from the platform. Restricted to Platform Admin."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security Violation: You cannot delete your own active administrator account."
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    username_deleted = target_user.username
    db.delete(target_user)
    db.commit()

    return {
        "status": "success",
        "message": f"User '{username_deleted}' (ID: {user_id}) and credentials have been permanently removed from database."
    }

@router.patch("/{user_id}/toggle-active", response_model=UserResponse)
def toggle_user_active(
    user_id: int,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Toggle user active/inactive status. Restricted to Platform Admin."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)

    res = UserResponse.model_validate(user)
    res.organization_name = user.organization.name if user.organization else None
    res.pickup_partner_name = user.pickup_partner.name if user.pickup_partner else None
    return res
