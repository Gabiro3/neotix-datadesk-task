from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.logging import RequestLogMiddleware, configure_logging
from app.routers import analytics, auth, episodes, events, requests, users
from app.schemas import HealthOut

configure_logging()

app = FastAPI(title="Dataset Request Desk", version="1.0.0")
app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(requests.router)
app.include_router(episodes.router)
app.include_router(analytics.router)
app.include_router(users.router)
app.include_router(events.router)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    return HealthOut(status="ok" if db_status == "ok" else "degraded", database=db_status)
