from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Assignment, Episode, EpisodeQuality, User, UserRole
from app.schemas import EpisodeOut, ImportResult
from app.security import require_roles
from app.services.import_episodes import import_episodes

router = APIRouter(tags=["episodes"])


@router.get("/episodes", response_model=list[EpisodeOut])
def list_episodes(
    task_name: str | None = Query(default=None),
    quality: EpisodeQuality | None = Query(default=None),
    available_only: bool = Query(default=False),
    user: User = Depends(require_roles(UserRole.operator, UserRole.admin)),
    db: Session = Depends(get_db),
):
    query = select(Episode).options(selectinload(Episode.assignment)).order_by(Episode.recorded_at.desc())
    if task_name:
        query = query.where(Episode.task_name.ilike(f"%{task_name.strip().lower()}%"))
    if quality:
        query = query.where(Episode.quality == quality)
    if available_only:
        query = query.outerjoin(Assignment).where(Assignment.id.is_(None))
    episodes = db.scalars(query.limit(500)).unique().all()
    return [
        EpisodeOut(
            id=ep.id,
            episode_id=ep.episode_id,
            robot_id=ep.robot_id,
            task_name=ep.task_name,
            recorded_at=ep.recorded_at,
            duration_seconds=ep.duration_seconds,
            operator_name=ep.operator_name,
            quality=ep.quality,
            assigned_request_id=ep.assignment.request_id if ep.assignment else None,
        )
        for ep in episodes
    ]


@router.post("/episodes/import", response_model=ImportResult)
def import_csv(
    file: UploadFile = File(...),
    user: User = Depends(require_roles(UserRole.operator, UserRole.admin)),
    db: Session = Depends(get_db),
):
    return import_episodes(db, file.file)
