from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole
from app.schemas import AssignmentIn, RequestCreateIn, RequestOut, RequestTransitionIn
from app.security import get_current_user, require_roles
from app.services import assignments as assignment_service
from app.services import requests as request_service

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=list[RequestOut])
def list_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return request_service.list_requests(db, user)


@router.post("", response_model=RequestOut, status_code=201)
async def create_request(
    payload: RequestCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await request_service.create_request(db, user, payload)


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return request_service.get_request(db, user, request_id)


@router.post("/{request_id}/transition", response_model=RequestOut)
async def transition(
    request_id: int,
    payload: RequestTransitionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await request_service.transition_request(db, user, request_id, payload.status, payload.note)


@router.post("/{request_id}/assignments")
async def assign(
    request_id: int,
    payload: AssignmentIn,
    user: User = Depends(require_roles(UserRole.operator, UserRole.admin)),
    db: Session = Depends(get_db),
):
    return await assignment_service.assign_episodes(db, user, request_id, payload.episode_ids)


@router.delete("/{request_id}/assignments/{episode_id}")
async def unassign(
    request_id: int,
    episode_id: str,
    user: User = Depends(require_roles(UserRole.operator, UserRole.admin)),
    db: Session = Depends(get_db),
):
    return await assignment_service.unassign_episode(db, user, request_id, episode_id)
