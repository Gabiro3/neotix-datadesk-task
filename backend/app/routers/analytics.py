from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EpisodeQuality, User, UserRole
from app.schemas import AnalyticsOut
from app.security import require_roles
from app.services.analytics import get_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
def analytics(
    start: datetime = Query(...),
    end: datetime = Query(...),
    operator_name: str | None = Query(default=None),
    robot_id: str | None = Query(default=None),
    task_name: str | None = Query(default=None),
    quality: EpisodeQuality | None = Query(default=None),
    user: User = Depends(require_roles(UserRole.operator, UserRole.admin)),
    db: Session = Depends(get_db),
):
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return get_analytics(
        db,
        start,
        end,
        operator_name=operator_name,
        robot_id=robot_id,
        task_name=task_name,
        quality=quality,
    )
