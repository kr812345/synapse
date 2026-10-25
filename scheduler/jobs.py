"""Durable jobs. Cron and one-shot alarms survive a restart."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

DEFAULT_PATH = "/var/lib/pip/jobs.sqlite"
DEFAULT_TZ = "Asia/Kolkata"


def _connect(path: str) -> sqlite3.Connection:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


class JobStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("PIP_JOBS_PATH", DEFAULT_PATH)
        self.conn = _connect(self.path)
        self._init()

    def _init(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                kind TEXT NOT NULL,
                schedule TEXT,
                timezone TEXT NOT NULL,
                payload TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                quiet_start TEXT,
                quiet_end TEXT,
                last_run TEXT,
                next_run TEXT,
                status TEXT
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert(
        self,
        name: str,
        kind: str,
        schedule: str,
        payload: dict,
        timezone_name: str = DEFAULT_TZ,
        enabled: bool = True,
        quiet_start: Optional[str] = None,
        quiet_end: Optional[str] = None,
        next_run: Optional[datetime] = None,
    ) -> dict:
        now = datetime.now(ZoneInfo(timezone_name))
        if next_run is None:
            next_run = initial_next_run(kind, schedule, now, timezone_name)
        row = {
            "id": str(uuid.uuid4()),
            "name": name,
            "kind": kind,
            "schedule": schedule,
            "timezone": timezone_name,
            "payload": json.dumps(payload),
            "enabled": 1 if enabled else 0,
            "quiet_start": quiet_start,
            "quiet_end": quiet_end,
            "last_run": None,
            "next_run": next_run.isoformat() if next_run else None,
            "status": "scheduled",
        }
        existing = self.conn.execute("SELECT id FROM jobs WHERE name = ?", (name,)).fetchone()
        if existing:
            self.conn.execute(
                """
                UPDATE jobs
                SET kind=?, schedule=?, timezone=?, payload=?, enabled=?,
                    quiet_start=?, quiet_end=?, next_run=?, status=?
                WHERE name=?
                """,
                (
                    row["kind"],
                    row["schedule"],
                    row["timezone"],
                    row["payload"],
                    row["enabled"],
                    row["quiet_start"],
                    row["quiet_end"],
                    row["next_run"],
                    row["status"],
                    name,
                ),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO jobs (
                    id, name, kind, schedule, timezone, payload, enabled,
                    quiet_start, quiet_end, last_run, next_run, status
                ) VALUES (
                    :id, :name, :kind, :schedule, :timezone, :payload, :enabled,
                    :quiet_start, :quiet_end, :last_run, :next_run, :status
                )
                """,
                row,
            )
        self.conn.commit()
        return self.get_by_name(name)

    def get_by_name(self, name: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM jobs WHERE name = ?", (name,)).fetchone()
        return _row_to_dict(row) if row else None

    def list_jobs(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM jobs ORDER BY name").fetchall()
        return [_row_to_dict(row) for row in rows]

    def claim_due(self, now: datetime) -> list[dict]:
        due: list[dict] = []
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE enabled = 1 AND next_run IS NOT NULL"
        ).fetchall()
        for row in rows:
            job = _row_to_dict(row)
            when = _parse_dt(job["next_run"])
            if when is None or when > now:
                continue
            if in_quiet_hours(now, job):
                continue
            job["status"] = "running"
            self.conn.execute("UPDATE jobs SET status = ? WHERE id = ?", ("running", job["id"]))
            due.append(job)
        self.conn.commit()
        return due

    def mark_ran(self, job: dict, now: datetime) -> dict:
        tz = ZoneInfo(job["timezone"])
        local_now = now.astimezone(tz)
        if job["kind"] == "alarm":
            self.conn.execute(
                """
                UPDATE jobs
                SET enabled = 0, last_run = ?, next_run = NULL, status = ?
                WHERE id = ?
                """,
                (local_now.isoformat(), "done", job["id"]),
            )
        else:
            nxt = next_cron(job["schedule"], local_now + timedelta(seconds=1), job["timezone"])
            self.conn.execute(
                """
                UPDATE jobs
                SET last_run = ?, next_run = ?, status = ?
                WHERE id = ?
                """,
                (local_now.isoformat(), nxt.isoformat() if nxt else None, "scheduled", job["id"]),
            )
        self.conn.commit()
        return self.get_by_name(job["name"])


def _row_to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["enabled"] = bool(data["enabled"])
    try:
        data["payload"] = json.loads(data["payload"])
    except (TypeError, json.JSONDecodeError):
        data["payload"] = {}
    return data


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def in_quiet_hours(now: datetime, job: dict) -> bool:
    start = job.get("quiet_start")
    end = job.get("quiet_end")
    if not start or not end:
        return False
    local = now.astimezone(ZoneInfo(job["timezone"])).strftime("%H:%M")
    if start <= end:
        return start <= local < end
    return local >= start or local < end


def initial_next_run(kind: str, schedule: str, now: datetime, timezone_name: str) -> datetime:
    if kind == "alarm":
        if schedule:
            parsed = datetime.fromisoformat(schedule)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
            return parsed
        local = now.astimezone(ZoneInfo(timezone_name))
        tomorrow = (local + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return tomorrow
    if kind == "cron":
        return next_cron(schedule, now + timedelta(minutes=1), timezone_name)
    return now + timedelta(days=1)


def _field_match(field: str, value: int) -> bool:
    if field == "*":
        return True
    for part in field.split(","):
        if part.startswith("*/"):
            step = int(part[2:])
            if step > 0 and value % step == 0:
                return True
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            if int(start_s) <= value <= int(end_s):
                return True
            continue
        if int(part) == value:
            return True
    return False


def cron_matches(expression: str, moment: datetime) -> bool:
    fields = expression.split()
    if len(fields) != 5:
        return False
    minute, hour, day, month, dow = fields
    cron_dow = (moment.weekday() + 1) % 7
    return (
        _field_match(minute, moment.minute)
        and _field_match(hour, moment.hour)
        and _field_match(day, moment.day)
        and _field_match(month, moment.month)
        and _field_match(dow, cron_dow)
    )


def next_cron(expression: str, after: datetime, timezone_name: str) -> Optional[datetime]:
    tz = ZoneInfo(timezone_name)
    cursor = after.astimezone(tz).replace(second=0, microsecond=0)
    for _ in range(60 * 24 * 8):
        cursor += timedelta(minutes=1)
        if cron_matches(expression, cursor):
            return cursor
    return None


def seed_default_jobs(store: JobStore) -> list[dict]:
    """Install the alarm and the repeating browser check once each."""
    created = []
    specs = [
        {
            "name": "pip-hello-alarm",
            "kind": "alarm",
            "schedule": "",
            "payload": {"type": "notify", "message": "Pip here. One thing is due."},
        },
        {
            "name": "pip-page-check",
            "kind": "cron",
            "schedule": "*/30 * * * *",
            "payload": {"tool": "browser_open", "url": "https://example.com"},
            "quiet_start": "23:00",
            "quiet_end": "07:00",
        },
    ]
    for spec in specs:
        if store.get_by_name(spec["name"]):
            created.append(store.get_by_name(spec["name"]))
            continue
        created.append(store.upsert(**spec))
    return created


def install_default_jobs() -> None:
    try:
        store = JobStore()
        try:
            seed_default_jobs(store)
        finally:
            store.close()
    except Exception as exc:
        print(f"[jobs] default jobs not installed: {exc}")
