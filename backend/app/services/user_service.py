from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import UserCreate


def create_user(db: Session, data: UserCreate) -> User:
    user = User(name=data.name, role=data.role)
    db.add(user)
    db.commit()
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))
