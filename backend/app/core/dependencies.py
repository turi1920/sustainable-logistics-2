from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.database import get_db
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: Optional[str] = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{current_user.role}' is not authorized to perform this action. Required: {allowed_roles}"
            )
        return current_user
    return role_checker

def validate_retailer_access(current_user: User, return_obj: ReturnRequest) -> None:
    """Enforces multi-tenant isolation.
    If the user has role RETAILER, they can ONLY access returns belonging to their organization.
    """
    if current_user.role == "RETAILER":
        if return_obj.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access records belonging to another retailer organization."
            )

def validate_partner_access(current_user: User, return_obj: ReturnRequest) -> None:
    """Enforces multi-tenant carrier isolation for pickup partners.
    If the user has role PICKUP_PARTNER, they can ONLY access returns assigned to their carrier.
    """
    if current_user.role == "PICKUP_PARTNER":
        if return_obj.pickup_partner_id != current_user.pickup_partner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access shipments assigned to another pickup carrier."
            )
