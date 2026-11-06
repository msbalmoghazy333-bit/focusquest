from datetime import date, timedelta

from focusquest.core import stats


def _session(start: str, worked: int, completed: bool, task: str = "t",
             violations: int = 0) -> dict:
    return {"start": start, "worked_sec": worked, "planned_sec": 1500,
            "completed": completed, "task": task, "violations": violations}


def test_record_session_aggregates_day_bucket():
    data = {"sessions": [], "days": {}}
    stats.record_session(data, _session("2026-11-06T10:00:00", 1500, True))
    stats.record_session(data, _session("2026-11-06T12:00:00", 900, False, violations=1))
    bucket = data["days"]["2026-11-06"]
    assert bucket["focus_sec"] == 2400
    assert bucket["sessions_done"] == 1
    assert bucket["sessions_aborted"] == 1
    assert bucket["violations"] == 1
    assert len(data["sessions"]) == 2


def test_weekly_series_is_seven_days_ending_today():
    today = date(2026, 11, 6)
    series = stats.weekly_series({}, today)
    assert len(series) == 7
    assert series[-1]["date"] == "2026-11-06"
    assert series[0]["date"] == "2026-10-31"
    assert all(point["minutes"] == 0 for point in series)


def test_headline_and_streak():
    today = date(2026, 11, 6)
    days = {}
    for i, done in ((3, 1), (2, 2), (1, 1), (0, 3)):
        d = (today - timedelta(days=i)).isoformat()
        days[d] = {"focus_sec": 1500 * done, "sessions_done": done,
                   "sessions_aborted": 0, "violations": 0}
    h = stats.headline(days, today)
    assert h["streak_days"] == 4
    assert h["today_minutes"] == 75
    assert h["week_minutes"] == (1 + 2 + 1 + 3) * 25
    assert h["best_minutes"] == 75


def test_completed_today_filters_today_only():
    today = date.today().isoformat()
    other = (date.today() - timedelta(days=1)).isoformat()
    data = {"sessions": [
        _session(f"{today}T09:00:00", 1500, True, "مهمة اليوم"),
        _session(f"{today}T10:00:00", 1500, False, "مكسورة"),
        _session(f"{other}T09:00:00", 1500, True, "أمس"),
    ]}
    done = stats.completed_today(data)
    assert [s["task"] for s in done] == ["مهمة اليوم"]
