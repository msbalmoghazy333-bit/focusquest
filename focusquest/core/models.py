"""Shared data shapes (plain dataclasses, kept out of the hot path)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class SessionRecord:
    start: str
    worked_sec: int
    planned_sec: int
    completed: bool
    task: str = ""
    violations: int = 0

    @classmethod
    def now(cls, planned_sec: int) -> "SessionRecord":
        return cls(start=datetime.now().isoformat(timespec="seconds"),
                   worked_sec=0, planned_sec=planned_sec, completed=False)

    def to_dict(self) -> dict:
        return asdict(self)
