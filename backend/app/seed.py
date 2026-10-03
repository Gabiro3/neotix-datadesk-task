import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserRole
from app.security import hash_password


def seed_users(db: Session, path: str | None = None) -> int:
    seed_path = Path(path or settings.seed_users_path)
    if not seed_path.exists():
        local = Path(__file__).resolve().parents[2] / "seed" / "users.json"
        seed_path = local
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    created = 0
    for row in data:
        email = row["email"].lower()
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            continue
        db.add(
            User(
                email=email,
                password_hash=hash_password(row["password"]),
                name=row["name"],
                role=UserRole(row["role"]),
                organisation=row.get("organisation"),
                is_active=True,
                must_change_password=False,
            )
        )
        created += 1
    db.commit()
    return created
