"""Quiet hours and cron fields, including the Sunday weekday conversion."""

from datetime import datetime
from zoneinfo import ZoneInfo

from scheduler.jobs import cron_matches, in_quiet_hours, next_cron, seed_default_jobs, JobStore


KOLKATA = ZoneInfo("Asia/Kolkata")


def test_quiet_hours_wrap_overnight_and_stop_at_the_end():
    job = {"timezone": "Asia/Kolkata", "quiet_start": "23:00", "quiet_end": "07:00"}
    assert in_quiet_hours(datetime(2026, 10, 25, 23, 30, tzinfo=KOLKATA), job) is True
    assert in_quiet_hours(datetime(2026, 10, 26, 6, 59, tzinfo=KOLKATA), job) is True
    assert in_quiet_hours(datetime(2026, 10, 26, 7, 0, tzinfo=KOLKATA), job) is False
    assert in_quiet_hours(datetime(2026, 10, 26, 10, 0, tzinfo=KOLKATA), job) is False


def test_quiet_hours_same_day_window():
    job = {"timezone": "Asia/Kolkata", "quiet_start": "12:00", "quiet_end": "13:00"}
    assert in_quiet_hours(datetime(2026, 10, 26, 12, 30, tzinfo=KOLKATA), job) is True
    assert in_quiet_hours(datetime(2026, 10, 26, 13, 0, tzinfo=KOLKATA), job) is False
    assert in_quiet_hours(datetime(2026, 10, 26, 12, 30, tzinfo=KOLKATA), {"timezone": "Asia/Kolkata"}) is False


def test_cron_weekday_uses_sunday_as_zero():
    sunday = datetime(2026, 10, 25, 9, 0, tzinfo=KOLKATA)
    monday = datetime(2026, 10, 26, 9, 0, tzinfo=KOLKATA)
    assert sunday.weekday() == 6
    assert cron_matches("0 9 * * 0", sunday) is True
    assert cron_matches("0 9 * * 0", monday) is False
    assert cron_matches("0 9 * * 1-5", monday) is True
    assert cron_matches("0 9 * * 1-5", sunday) is False
    assert cron_matches("*/30 * * * *", datetime(2026, 10, 26, 10, 30, tzinfo=KOLKATA)) is True
    assert cron_matches("*/30 * * * *", datetime(2026, 10, 26, 10, 15, tzinfo=KOLKATA)) is False
    assert cron_matches("* * *", sunday) is False


def test_next_cron_steps_to_the_following_mark():
    after = datetime(2026, 10, 26, 10, 0, tzinfo=KOLKATA)
    found = next_cron("*/30 * * * *", after, "Asia/Kolkata")
    assert found == datetime(2026, 10, 26, 10, 30, tzinfo=KOLKATA)


def test_default_jobs_are_seeded_once(isolate_pip_files):
    store = JobStore()
    try:
        first = seed_default_jobs(store)
        second = seed_default_jobs(store)
        assert {job["name"] for job in first} == {"pip-hello-alarm", "pip-page-check"}
        assert {job["id"] for job in first} == {job["id"] for job in second}
    finally:
        store.close()
