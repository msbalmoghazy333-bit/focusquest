"""XP, levels and badge rules. Pure Python — unit tested.

Level curve: moving from level n to n + 1 costs ``100 * n`` XP.
Cumulative XP required to *reach* level L is therefore ``50 * L * (L - 1)``.
"""
from __future__ import annotations

FOCUS_MINUTE_XP = 1
SESSION_COMPLETE_BONUS = 5
EARLY_QUIT_PENALTY = 10
VIOLATION_PENALTY = 5
MIN_XP = 0


def xp_needed_for_level(level: int) -> int:
    """XP cost to level up *from* ``level`` to level + 1."""
    if level < 1:
        level = 1
    return 100 * level


def xp_to_reach_level(level: int) -> int:
    """Total cumulative XP required to be *at* ``level``."""
    if level <= 1:
        return 0
    return 50 * level * (level - 1)


def level_for_xp(total_xp: int) -> int:
    xp = max(0, total_xp)
    level = 1
    while xp_to_reach_level(level + 1) <= xp:
        level += 1
    return level


def xp_progress(total_xp: int) -> dict:
    """Progress toward the next level for UI rendering."""
    xp = max(0, total_xp)
    level = level_for_xp(xp)
    base = xp_to_reach_level(level)
    needed = xp_needed_for_level(level)
    into = xp - base
    return {
        "level": level,
        "into_level": into,
        "needed_for_next": needed,
        "progress": (into / needed) if needed else 1.0,
        "total_xp": xp,
    }


def grant_focus_minutes(data: dict, minutes: int) -> dict:
    gain = max(0, minutes) * FOCUS_MINUTE_XP
    data["xp"] = max(MIN_XP, int(data.get("xp", 0)) + gain)
    return data


def grant_session_bonus(data: dict) -> dict:
    data["xp"] = max(MIN_XP, int(data.get("xp", 0)) + SESSION_COMPLETE_BONUS)
    return data


def apply_penalty(data: dict, amount: int) -> int:
    """Apply an XP loss; returns the amount actually deducted."""
    xp = int(data.get("xp", 0))
    new_xp = max(MIN_XP, xp - max(0, amount))
    data["xp"] = new_xp
    return xp - new_xp


# --------------------------------------------------------------------------- badges
LEVEL_UP = "level_up"
BADGES = {
    "first_session": {
        "en": ("First Focused Session", "Complete your very first focus session."),
        "ar": ("أول جلسة تركيز", "أكمل أول جلسة مذاكرة كاملة."),
    },
    "perfect_day": {
        "en": ("Perfect Day", "Complete 4 focus sessions in a single day."),
        "ar": ("يوم مثالي", "أكمل 4 جلسات تركيز في يوم واحد."),
    },
    "streak_3": {
        "en": ("Three-Day Streak", "Focus at least once on 3 consecutive days."),
        "ar": ("٣ أيام متتالية", "ذاكر مرة واحدة على الأقل ٣ أيام متتالية."),
    },
    "ten_hours": {
        "en": ("Ten Focused Hours", "Accumulate 10 hours of focused time."),
        "ar": ("١٠ ساعات تركيز", "اجمع ١٠ ساعات تركيز تراكمي."),
    },
    "no_distraction": {
        "en": ("Laser Focus", "Complete a full session with zero distractions."),
        "ar": ("تركيز شعاعي", "أكمل جلسة كاملة بدون أي إلهاء."),
    },
}


def evaluate_badges(data: dict) -> list[str]:
    """Return badge ids earned but not yet awarded. Mutates nothing."""
    earned = set(data.get("badges", []))
    days = data.get("days", {})
    sessions = data.get("sessions", [])
    total_focus_sec = sum(int(d.get("focus_sec", 0)) for d in days.values())
    completed_sessions = sum(1 for s in sessions if s.get("completed"))
    out = []

    def award(badge_id: str, condition: bool) -> None:
        if condition and badge_id not in earned:
            out.append(badge_id)

    award("first_session", completed_sessions >= 1)
    award("ten_hours", total_focus_sec >= 10 * 3600)
    award("perfect_day", any(int(d.get("sessions_done", 0)) >= 4 for d in days.values()))
    award("no_distraction", any(
        s.get("completed") and int(s.get("violations", 0)) == 0 for s in sessions
    ))
    award("streak_3", _best_streak(days) >= 3)
    return out


def award_badges(data: dict) -> list[str]:
    newly = evaluate_badges(data)
    if newly:
        owned = list(data.get("badges", []))
        owned.extend(newly)
        data["badges"] = owned
    return newly


def _best_streak(days: dict) -> int:
    from datetime import date, timedelta

    if not days:
        return 0
    present = set()
    for key in days:
        try:
            d = date.fromisoformat(key)
        except ValueError:
            continue
        if int(days[key].get("sessions_done", 0)) > 0:
            present.add(d)
    if not present:
        return 0
    best = cur = 1
    ordered = sorted(present)
    for prev, cur_d in zip(ordered, ordered[1:]):
        if cur_d - prev == timedelta(days=1):
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best
