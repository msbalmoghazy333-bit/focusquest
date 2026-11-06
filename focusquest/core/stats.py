"""Aggregation of raw session history into charts and headline numbers.

Session schema (stored inside data["sessions"]):
    {"start": iso8601, "worked_sec": int, "planned_sec": int,
     "completed": bool, "task": str, "violations": int}

Derived day bucket (data["days"]["YYYY-MM-DD"]):
    {"focus_sec": int, "sessions_done": int, "sessions_aborted": int,
     "violations": int}
"""
from __future__ import annotations

from datetime import date, datetime, timedelta


def record_session(data: dict, session: dict) -> dict:
    started = session.get("start")
    try:
        day = datetime.fromisoformat(started).date() if started else date.today()
    except (TypeError, ValueError):
        day = date.today()
    key = day.isoformat()
    days = data.setdefault("days", {})
    bucket = days.setdefault(
        key, {"focus_sec": 0, "sessions_done": 0, "sessions_aborted": 0, "violations": 0}
    )
    worked = max(0, int(session.get("worked_sec", 0)))
    bucket["focus_sec"] += worked
    if session.get("completed"):
        bucket["sessions_done"] += 1
    else:
        bucket["sessions_aborted"] += 1
    bucket["violations"] += max(0, int(session.get("violations", 0)))
    sessions = data.setdefault("sessions", [])
    sessions.append(session)
    return data


def day_minutes(days: dict, day: date) -> int:
    return int(days.get(day.isoformat(), {}).get("focus_sec", 0)) // 60


def weekly_series(days: dict, today: date | None = None) -> list[dict]:
    """Last 7 calendar days oldest → newest, zero-filled."""
    today = today or date.today()
    out = []
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        out.append({
            "date": d.isoformat(),
            "minutes": day_minutes(days, d),
            "is_today": d == today,
        })
    return out


def headline(days: dict, today: date | None = None) -> dict:
    """Numbers for the stats page: today, this week, best day, streak."""
    today = today or date.today()
    week = weekly_series(days, today)
    today_min = week[-1]["minutes"]
    week_min = sum(w["minutes"] for w in week)
    best = max((day_minutes(days, d) for d in
                [today - timedelta(days=i) for i in range(7)]), default=0)
    return {
        "today_minutes": today_min,
        "week_minutes": week_min,
        "best_minutes": best,
        "streak_days": current_streak(days, today),
    }


def current_streak(days: dict, today: date | None = None) -> int:
    """Consecutive days up to today with at least one completed session."""
    today = today or date.today()
    streak = 0
    d = today
    while int(days.get(d.isoformat(), {}).get("sessions_done", 0)) > 0:
        streak += 1
        d -= timedelta(days=1)
    return streak


def completed_today(data: dict, today: date | None = None) -> list[dict]:
    today = today or date.today()
    out = []
    for s in data.get("sessions", []):
        try:
            d = datetime.fromisoformat(s.get("start", "")).date()
        except (TypeError, ValueError):
            continue
        if d == today and s.get("completed"):
            out.append(s)
    return out
