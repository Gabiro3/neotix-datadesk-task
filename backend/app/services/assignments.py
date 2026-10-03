from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.events import bus
from app.models import Assignment, Episode, EpisodeQuality, RequestStatus, User
from app.services.requests import _load_request, to_request_out


ASSIGNABLE = {EpisodeQuality.good, EpisodeQuality.usable} # Only consider episodes that are good and usable
ASSIGNABLE_STATUSES = {RequestStatus.submitted, RequestStatus.in_progress, RequestStatus.rejected}


async def assign_episodes(db: Session, user: User, request_id: int, episode_ids: list[str]) -> dict:
    request = _load_request(db, request_id)
    if request.status not in ASSIGNABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Can only assign episodes while the request is open for work",
        )

    unique_ids = list(dict.fromkeys(episode_ids))
    episodes = db.scalars(select(Episode).where(Episode.episode_id.in_(unique_ids))).all()
    found = {ep.episode_id: ep for ep in episodes}
    errors: list[str] = []
    to_assign: list[Episode] = []

    existing = {
        a.episode_id: a
        for a in db.scalars(
            select(Assignment).options(selectinload(Assignment.episode)).where(
                Assignment.episode_id.in_([ep.id for ep in episodes])
            )
        ).all()
    }

    for code in unique_ids:
        episode = found.get(code)
        if episode is None:
            errors.append(f"{code}: not found")
            continue
        if episode.quality not in ASSIGNABLE:
            errors.append(f"{code}: quality {episode.quality.value} cannot be assigned")
            continue
        current = existing.get(episode.id)
        if current is not None:
            if current.request_id == request.id:
                continue
            errors.append(f"{code}: already assigned to request {current.request_id}")
            continue
        to_assign.append(episode)

    if errors:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"errors": errors})

    for episode in to_assign:
        db.add(Assignment(request_id=request.id, episode_id=episode.id, assigned_by_id=user.id))
    db.commit()
    request = _load_request(db, request.id)
    out = to_request_out(db, request, include_detail=True)
    await bus.publish("request.updated", out.model_dump(mode="json"))
    return {"assigned": len(to_assign), "request": out}


async def unassign_episode(db: Session, user: User, request_id: int, episode_code: str) -> dict:
    request = _load_request(db, request_id)
    if request.status not in ASSIGNABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot unassign after delivery",
        )
    episode = db.scalar(select(Episode).where(Episode.episode_id == episode_code))
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    assignment = db.scalar(
        select(Assignment).where(Assignment.request_id == request.id, Assignment.episode_id == episode.id)
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    request = _load_request(db, request.id)
    out = to_request_out(db, request, include_detail=True)
    await bus.publish("request.updated", out.model_dump(mode="json"))
    return {"unassigned": episode_code, "request": out}
