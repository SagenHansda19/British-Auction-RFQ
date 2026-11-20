from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.user import UserCreate, UserOut
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, data)


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return user_service.list_users(db)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
