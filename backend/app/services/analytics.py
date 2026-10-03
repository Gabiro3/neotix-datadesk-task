from datetime import datetime

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models import Episode, EpisodeQuality, Request, RequestEvent, RequestStatus
from app.schemas import AnalyticsOut


def get_analytics(
    db: Session,
    start: datetime,
    end: datetime,
    operator_name: str | None = None,
    robot_id: str | None = None,
    task_name: str | None = None,
    quality: EpisodeQuality | None = None,
) -> AnalyticsOut:
    episode_filters = [Episode.recorded_at >= start, Episode.recorded_at <= end]
    if operator_name:
        episode_filters.append(Episode.operator_name == operator_name)
    if robot_id:
        episode_filters.append(Episode.robot_id == robot_id)
    if task_name:
        episode_filters.append(Episode.task_name == task_name)
    if quality:
        episode_filters.append(Episode.quality == quality)

    episodes_rows = db.execute(
        select(
            cast(Episode.recorded_at, Date).label("day"),
            Episode.robot_id,
            func.count(Episode.id).label("count"),
        )
        .where(*episode_filters)
        .group_by("day", Episode.robot_id)
        .order_by("day", Episode.robot_id)
    ).all()

    status_rows = db.execute(
        select(Request.status, func.count(Request.id))
        .where(Request.created_at >= start, Request.created_at <= end)
        .group_by(Request.status)
    ).all()
    requests_by_status = {status.value: 0 for status in RequestStatus}
    for status, count in status_rows:
        requests_by_status[status.value] = count

    submitted = (
        select(
            RequestEvent.request_id.label("request_id"),
            func.min(RequestEvent.created_at).label("submitted_at"),
        )
        .where(RequestEvent.to_status == RequestStatus.submitted)
        .group_by(RequestEvent.request_id)
        .subquery()
    )
    delivered = (
        select(
            RequestEvent.request_id.label("request_id"),
            func.min(RequestEvent.created_at).label("delivered_at"),
        )
        .where(RequestEvent.to_status == RequestStatus.delivered)
        .group_by(RequestEvent.request_id)
        .subquery()
    )
    median_hours = db.execute(
        select(
            func.percentile_cont(0.5).within_group(
                func.extract("epoch", delivered.c.delivered_at - submitted.c.submitted_at) / 3600.0
            )
        )
        .select_from(submitted)
        .join(delivered, delivered.c.request_id == submitted.c.request_id)
        .where(submitted.c.submitted_at >= start, submitted.c.submitted_at <= end)
    ).scalar()

    top_filters = [
        Episode.quality == EpisodeQuality.good,
        Episode.recorded_at >= start,
        Episode.recorded_at <= end,
    ]
    if operator_name:
        top_filters.append(Episode.operator_name == operator_name)
    if robot_id:
        top_filters.append(Episode.robot_id == robot_id)
    if task_name:
        top_filters.append(Episode.task_name == task_name)

    top_rows = db.execute(
        select(Episode.task_name, func.count(Episode.id).label("count"))
        .where(*top_filters)
        .group_by(Episode.task_name)
        .order_by(func.count(Episode.id).desc(), Episode.task_name)
        .limit(5)
    ).all()

    option_date_filter = [Episode.recorded_at >= start, Episode.recorded_at <= end]
    operators = db.scalars(
        select(Episode.operator_name).where(*option_date_filter).distinct().order_by(Episode.operator_name)
    ).all()
    robots = db.scalars(
        select(Episode.robot_id).where(*option_date_filter).distinct().order_by(Episode.robot_id)
    ).all()
    tasks = db.scalars(
        select(Episode.task_name).where(*option_date_filter).distinct().order_by(Episode.task_name)
    ).all()

    return AnalyticsOut(
        episodes_per_day_per_robot=[
            {"day": str(day), "robot_id": robot_id, "count": count}
            for day, robot_id, count in episodes_rows
        ],
        requests_by_status=requests_by_status,
        median_submitted_to_delivered_hours=float(median_hours) if median_hours is not None else None,
        top_good_tasks=[{"task_name": name, "count": count} for name, count in top_rows],
        filter_options={
            "operators": list(operators),
            "robots": list(robots),
            "tasks": list(tasks),
            "qualities": [quality.value for quality in EpisodeQuality],
        },
    )
