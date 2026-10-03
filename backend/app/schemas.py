from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import EpisodeQuality, RequestStatus, UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: UserRole
    organisation: str | None
    is_active: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class UserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    role: UserRole
    organisation: str | None = None


class UserUpdateIn(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    name: str | None = None


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class RequestCreateIn(BaseModel):
    task_name: str = Field(min_length=1, max_length=255)
    episodes_requested: int = Field(ge=1, le=10000)
    deadline: datetime
    notes: str | None = None


class RequestTransitionIn(BaseModel):
    status: RequestStatus
    note: str | None = None


class AssignmentIn(BaseModel):
    episode_ids: list[str] = Field(min_length=1)


class EpisodeOut(BaseModel):
    id: int
    episode_id: str
    robot_id: str
    task_name: str
    recorded_at: datetime
    duration_seconds: int
    operator_name: str
    quality: EpisodeQuality
    assigned_request_id: int | None = None

    model_config = {"from_attributes": True}


class AssignmentOut(BaseModel):
    id: int
    episode: EpisodeOut
    assigned_at: datetime

    model_config = {"from_attributes": True}


class RequestEventOut(BaseModel):
    id: int
    actor_id: int
    actor_name: str
    from_status: RequestStatus | None
    to_status: RequestStatus
    note: str | None
    created_at: datetime


class RequestOut(BaseModel):
    id: int
    client_id: int
    client_name: str
    task_name: str
    episodes_requested: int
    assigned_count: int
    deadline: datetime
    notes: str | None
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    assignments: list[AssignmentOut] = []
    events: list[RequestEventOut] = []


class ImportSkip(BaseModel):
    row: int
    episode_id: str | None
    reason: str


class ImportResult(BaseModel):
    imported: int
    skipped: int
    updated: int
    skips: list[ImportSkip]


class AnalyticsOut(BaseModel):
    episodes_per_day_per_robot: list[dict]
    requests_by_status: dict[str, int]
    median_submitted_to_delivered_hours: float | None
    top_good_tasks: list[dict]
    filter_options: dict[str, list[str]]


class HealthOut(BaseModel):
    status: str
    database: str
