from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import BinaryIO, TextIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Episode, EpisodeQuality
from app.schemas import ImportResult, ImportSkip

KNOWN_ROBOTS = {"arm-01", "arm-02", "arm-03", "mobile-01", "humanoid-01"} # Hardcoded robot names for now, to change later
EPISODE_ID_RE = re.compile(r"^EP-\d+$", re.IGNORECASE)
MAX_DURATION = 3600
DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S%z",
)


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _parse_episode_id(raw: str) -> str | None:
    value = _norm(raw).upper()
    if not value or not EPISODE_ID_RE.match(value):
        return None
    prefix, number = value.split("-", 1)
    return f"{prefix}-{number.zfill(5)}"


def _parse_quality(raw: str) -> EpisodeQuality | None:
    value = _norm(raw).lower()
    try:
        return EpisodeQuality(value)
    except ValueError:
        return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(raw: str) -> datetime | None:
    value = _norm(raw)
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_duration(raw: str) -> int | None:
    value = _norm(raw)
    if not value or value.upper() == "N/A":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if number <= 0 or number > MAX_DURATION:
        return None
    return int(round(number))


def _normalize_task(raw: str) -> str | None:
    value = " ".join(_norm(raw).split())
    if not value:
        return None
    return value.lower()


def _open_text(source: str | BinaryIO | TextIO) -> TextIO:
    if isinstance(source, str):
        return open(source, encoding="utf-8", newline="")
    if hasattr(source, "read"):
        data = source.read()
        if isinstance(data, bytes):
            return io.StringIO(data.decode("utf-8"))
        return io.StringIO(data)
    raise TypeError("unsupported import source")


def import_episodes(db: Session, source: str | BinaryIO | TextIO) -> ImportResult:
    skips: list[ImportSkip] = []
    imported = 0
    updated = 0
    seen_in_file: dict[str, int] = {}

    handle = _open_text(source)
    close = handle is not source and not isinstance(source, io.StringIO)
    try:
        reader = csv.DictReader(handle)
        required = {
            "episode_id",
            "robot_id",
            "task_name",
            "recorded_at",
            "duration_seconds",
            "operator_name",
            "quality",
        }
        if reader.fieldnames is None or not required.issubset({f.strip() for f in reader.fieldnames}):
            raise ValueError("CSV is missing required columns")

        existing = {
            ep.episode_id: ep
            for ep in db.execute(select(Episode)).scalars().all()
        }

        for index, raw_row in enumerate(reader, start=2):
            row = {k.strip(): (v if v is not None else "") for k, v in raw_row.items() if k}
            if not any(_norm(v) for v in row.values()):
                continue

            episode_id = _parse_episode_id(row.get("episode_id", ""))
            if episode_id is None:
                skips.append(ImportSkip(row=index, episode_id=_norm(row.get("episode_id")) or None, reason="missing or invalid episode_id"))
                continue
            if episode_id in seen_in_file:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason=f"duplicate in file (first seen on row {seen_in_file[episode_id]})"))
                continue
            seen_in_file[episode_id] = index

            robot_id = _norm(row.get("robot_id")).lower()
            if robot_id not in KNOWN_ROBOTS:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="unknown or missing robot_id"))
                continue

            task_name = _normalize_task(row.get("task_name", ""))
            if task_name is None:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="missing task_name"))
                continue

            recorded_at = _parse_datetime(row.get("recorded_at", ""))
            if recorded_at is None:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="invalid recorded_at"))
                continue
            now = datetime.now(timezone.utc)
            if recorded_at.year < 2020 or recorded_at > now.replace(year=now.year + 1):
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="recorded_at out of range"))
                continue

            duration = _parse_duration(row.get("duration_seconds", ""))
            if duration is None:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="invalid duration_seconds"))
                continue

            operator_name = _norm(row.get("operator_name"))
            if not operator_name:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="missing operator_name"))
                continue

            quality = _parse_quality(row.get("quality", ""))
            if quality is None:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="invalid quality"))
                continue

            payload = {
                "episode_id": episode_id,
                "robot_id": robot_id,
                "task_name": task_name,
                "recorded_at": recorded_at,
                "duration_seconds": duration,
                "operator_name": operator_name,
                "quality": quality,
            }
            current = existing.get(episode_id)
            if current is None:
                episode = Episode(**payload)
                db.add(episode)
                existing[episode_id] = episode
                imported += 1
                continue

            changed = False
            for field, value in payload.items():
                current_value = getattr(current, field)
                if field == "recorded_at":
                    current_value = _as_utc(current_value)
                    value = _as_utc(value)
                if current_value != value:
                    setattr(current, field, payload[field])
                    changed = True
            if changed:
                updated += 1
            else:
                skips.append(ImportSkip(row=index, episode_id=episode_id, reason="already imported (unchanged)"))

        db.commit()
        return ImportResult(imported=imported, skipped=len(skips), updated=updated, skips=skips)
    finally:
        if close:
            handle.close()
