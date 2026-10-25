"""Minute runner for durable jobs. systemd starts this as pip-cron."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone

from scheduler.jobs import JobStore


def post_job(job: dict) -> None:
    url = os.environ.get("PIP_BRAIN_URL", "http://127.0.0.1:9100").rstrip("/") + "/internal/jobs/fire"
    body = json.dumps({"job": job}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def tick(store: JobStore, now: datetime, poster=post_job) -> list[dict]:
    fired = []
    for job in store.claim_due(now):
        try:
            poster(job)
            store.mark_ran(job, now)
            fired.append(job)
        except Exception as exc:
            store.conn.execute(
                "UPDATE jobs SET status = ? WHERE id = ?",
                (f"error: {exc}", job["id"]),
            )
            store.conn.commit()
    return fired


def main() -> None:
    store = JobStore()
    while True:
        tick(store, datetime.now(timezone.utc))
        time.sleep(60)


if __name__ == "__main__":
    main()
