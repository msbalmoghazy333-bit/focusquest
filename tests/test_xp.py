from focusquest.core import xp


def _fresh():
    return {"xp": 0, "badges": [], "sessions": [], "days": {}}


def test_level_curve_math():
    assert xp.xp_to_reach_level(1) == 0
    assert xp.xp_to_reach_level(2) == 100
    assert xp.xp_to_reach_level(3) == 300
    assert xp.xp_to_reach_level(4) == 600
    assert xp.level_for_xp(0) == 1
    assert xp.level_for_xp(99) == 1
    assert xp.level_for_xp(100) == 2
    assert xp.level_for_xp(299) == 2
    assert xp.level_for_xp(300) == 3


def test_progress_reports_into_level():
    p = xp.xp_progress(150)  # level 2, 50 into a 200 XP level
    assert p["level"] == 2
    assert p["into_level"] == 50
    assert p["needed_for_next"] == 200
    assert 0 < p["progress"] < 1


def test_penalties_clamp_at_zero():
    data = _fresh()
    data["xp"] = 3
    deducted = xp.apply_penalty(data, xp.EARLY_QUIT_PENALTY)
    assert deducted == 3
    assert data["xp"] == 0


def test_badges_first_session_and_no_distraction():
    data = _fresh()
    data["sessions"].append({"start": "2026-11-06T10:00:00", "completed": True,
                             "violations": 0, "worked_sec": 1500, "task": "x"})
    earned = xp.award_badges(data)
    assert "first_session" in earned
    assert "no_distraction" in earned
    # awarding twice never duplicates
    assert xp.evaluate_badges(data) == []


def test_badge_ten_hours_and_perfect_day():
    data = _fresh()
    data["days"]["2026-11-01"] = {"focus_sec": 10 * 3600, "sessions_done": 4,
                                  "sessions_aborted": 0, "violations": 2}
    earned = set(xp.award_badges(data))
    assert {"ten_hours", "perfect_day"} <= earned


def test_badge_streak_three_days():
    data = _fresh()
    for day in ("2026-11-04", "2026-11-05", "2026-11-06"):
        data["days"][day] = {"focus_sec": 600, "sessions_done": 1,
                             "sessions_aborted": 0, "violations": 0}
    assert "streak_3" in xp.evaluate_badges(data)
