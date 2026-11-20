from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, Unauthenticated
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole


def get_current_user(
    x_user_id: int | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if x_user_id is None:
        raise Unauthenticated("Missing X-User-Id header")
    user = db.get(User, x_user_id)
    if user is None:
        raise Unauthenticated(f"Unknown user {x_user_id}")
    return user


def get_buyer(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.BUYER:
        raise Forbidden("Only buyers can do this")
    return user


def get_supplier(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.SUPPLIER:
        raise Forbidden("Only suppliers can do this")
    return user
