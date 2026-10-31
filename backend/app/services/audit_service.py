from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.audit import ReturnStatusHistory
from backend.app.models.user import User


def record_status_change(
    db: Session,
    return_id: str,
    old_status: Optional[str],
    new_status: str,
    actor: User,
    action: str,
    details: Optional[str] = None
) -> ReturnStatusHistory:
    history_entry = ReturnStatusHistory(
        return_id=return_id,
        old_status=old_status,
        new_status=new_status,
        actor_username=actor.username,
        actor_role=actor.role,
        action=action,
        details=details
    )
    db.add(history_entry)
    db.flush()
    return history_entry
