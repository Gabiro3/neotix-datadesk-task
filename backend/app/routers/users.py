from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole
from app.schemas import UserCreateIn, UserOut, UserUpdateIn
from app.security import require_roles
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return user_service.list_users(db)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreateIn,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return user_service.create_user(db, payload)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
):
    return user_service.update_user(db, user_id, payload)
