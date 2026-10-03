from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.events import bus
from app.models import Assignment, Request, RequestEvent, RequestStatus, User, UserRole
from app.schemas import RequestCreateIn, RequestEventOut, RequestOut

OPERATOR_TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.submitted: {RequestStatus.in_progress},
    RequestStatus.in_progress: {RequestStatus.delivered},
    RequestStatus.rejected: {RequestStatus.in_progress},
}

CLIENT_TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.delivered: {RequestStatus.accepted, RequestStatus.rejected},
}


def assigned_count(db: Session, request_id: int) -> int:
    return db.scalar(
        select(func.count(Assignment.id)).where(Assignment.request_id == request_id)
    ) or 0


def to_request_out(db: Session, request: Request, include_detail: bool = False) -> RequestOut:
    events = []
    assignments = []
    if include_detail:
        for event in request.events:
            events.append(
                RequestEventOut(
                    id=event.id,
                    actor_id=event.actor_id,
                    actor_name=event.actor.name if event.actor else "unknown",
                    from_status=event.from_status,
                    to_status=event.to_status,
                    note=event.note,
                    created_at=event.created_at,
                )
            )
        for assignment in request.assignments:
            episode = assignment.episode
            assignments.append(
                {
                    "id": assignment.id,
                    "assigned_at": assignment.assigned_at,
                    "episode": {
                        "id": episode.id,
                        "episode_id": episode.episode_id,
                        "robot_id": episode.robot_id,
                        "task_name": episode.task_name,
                        "recorded_at": episode.recorded_at,
                        "duration_seconds": episode.duration_seconds,
                        "operator_name": episode.operator_name,
                        "quality": episode.quality,
                        "assigned_request_id": request.id,
                    },
                }
            )
    return RequestOut(
        id=request.id,
        client_id=request.client_id,
        client_name=request.client.name if request.client else "",
        task_name=request.task_name,
        episodes_requested=request.episodes_requested,
        assigned_count=len(request.assignments) if request.assignments else assigned_count(db, request.id),
        deadline=request.deadline,
        notes=request.notes,
        status=request.status,
        created_at=request.created_at,
        updated_at=request.updated_at,
        assignments=assignments,
        events=events,
    )


def _load_request(db: Session, request_id: int) -> Request:
    request = db.scalar(
        select(Request)
        .options(
            selectinload(Request.client),
            selectinload(Request.events).selectinload(RequestEvent.actor),
            selectinload(Request.assignments).selectinload(Assignment.episode),
        )
        .where(Request.id == request_id)
    )
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return request


def list_requests(db: Session, user: User) -> list[RequestOut]:
    query = select(Request).options(
        selectinload(Request.client),
        selectinload(Request.assignments),
    ).order_by(Request.created_at.desc())
    if user.role == UserRole.client:
        query = query.where(Request.client_id == user.id)
    return [to_request_out(db, r) for r in db.scalars(query).all()]


def get_request(db: Session, user: User, request_id: int) -> RequestOut:
    request = _load_request(db, request_id)
    if user.role == UserRole.client and request.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return to_request_out(db, request, include_detail=True)


async def create_request(db: Session, user: User, payload: RequestCreateIn) -> RequestOut:
    if user.role != UserRole.client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can create requests")
    deadline = payload.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deadline must be in the future")

    request = Request(
        client_id=user.id,
        task_name=" ".join(payload.task_name.split()).lower(),
        episodes_requested=payload.episodes_requested,
        deadline=deadline,
        notes=payload.notes,
        status=RequestStatus.submitted,
    )
    db.add(request)
    db.flush()
    db.add(
        RequestEvent(
            request_id=request.id,
            actor_id=user.id,
            from_status=None,
            to_status=RequestStatus.submitted,
            note="Request submitted",
        )
    )
    db.commit()
    request = _load_request(db, request.id)
    out = to_request_out(db, request, include_detail=True)
    await bus.publish("request.created", out.model_dump(mode="json"))
    return out


async def transition_request(
    db: Session, user: User, request_id: int, new_status: RequestStatus, note: str | None
) -> RequestOut:
    request = _load_request(db, request_id)
    if user.role == UserRole.client:
        if request.client_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        allowed = CLIENT_TRANSITIONS.get(request.status, set())
    elif user.role in {UserRole.operator, UserRole.admin}:
        allowed = OPERATOR_TRANSITIONS.get(request.status, set())
    else:
        allowed = set()

    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot move from {request.status.value} to {new_status.value}",
        )

    if new_status == RequestStatus.delivered:
        count = assigned_count(db, request.id)
        if count < request.episodes_requested:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Need {request.episodes_requested} assigned episodes, have {count}",
            )

    event = RequestEvent(
        request_id=request.id,
        actor_id=user.id,
        from_status=request.status,
        to_status=new_status,
        note=note,
    )
    request.status = new_status
    db.add(event)
    db.commit()
    request = _load_request(db, request.id)
    out = to_request_out(db, request, include_detail=True)
    await bus.publish("request.updated", out.model_dump(mode="json"))
    return out
