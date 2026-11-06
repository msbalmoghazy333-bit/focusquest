"""JSON persistence with atomic writes and automatic backup/restore.

Data lives in ``%APPDATA%\\FocusQuest\\data.json`` on Windows (falls back to
home directory elsewhere). Writes go through a temporary file + os.replace so
an interruption can never corrupt the main file; the previous good file is
kept as ``data.json.bak`` and used to recover from corruption.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SCHEMA_VERSION = 1
APP_DIR_NAME = "FocusQuest"
DATA_FILE = "data.json"
BAK_FILE = "data.json.bak"
TMP_FILE = "data.json.tmp"


def default_data() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "xp": 0,
        "badges": [],
        "settings": {
            "focus_minutes": 25,
            "break_minutes": 5,
            "long_break_minutes": 15,
            "sessions_until_long_break": 4,
            "strict_mode_default": True,
            "language": "ar",
            "blacklist_apps": ["instagram.exe", "steam.exe"],
            "blacklist_sites": ["youtube", "twitter", "facebook", "tiktok"],
        },
        "sessions": [],
        "days": {},
    }


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    path = Path(base) / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_path() -> Path:
    return app_data_dir() / DATA_FILE


def backup_path() -> Path:
    return app_data_dir() / BAK_FILE


def load() -> dict:
    target = data_path()
    if not target.exists():
        return default_data()
    try:
        return _read(target)
    except (json.JSONDecodeError, OSError, KeyError):
        # self-heal from backup before giving up
        bak = backup_path()
        if bak.exists():
            try:
                healed = _read(bak)
                save(healed)
                return healed
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        return default_data()


def save(data: dict) -> None:
    data["schema_version"] = SCHEMA_VERSION
    target = data_path()
    tmp = target.with_name(TMP_FILE)
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    if target.exists():
        try:
            backup_path().write_bytes(target.read_bytes())
        except OSError:
            pass  # backup best-effort, never fatal
    os.replace(tmp, target)


def _read(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise KeyError("root must be an object")
    return _merge_defaults(data)


def _merge_defaults(data: dict) -> dict:
    merged = default_data()
    for key, value in data.items():
        merged[key] = value
    merged.setdefault("settings", {})
    settings = default_data()["settings"]
    for key, value in settings.items():
        merged["settings"].setdefault(key, value)
    return merged


def reset_all() -> None:
    for fname in (DATA_FILE, BAK_FILE, TMP_FILE):
        p = app_data_dir() / fname
        try:
            p.unlink()
        except OSError:
            pass


class DataStore:
    """In-memory holder + atomic persistence + change listeners.

    Views subscribe via :meth:`subscribe` and are notified after every
    successful save. No Qt dependency — listeners are plain callables.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._listeners: list = []
        self.data = self._load()

    def _load(self) -> dict:
        if self._path is not None:
            for candidate in (self._path,
                              self._path.with_suffix(self._path.suffix + ".bak")):
                try:
                    with candidate.open("r", encoding="utf-8") as fh:
                        return _merge_defaults(json.load(fh))
                except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError):
                    continue
            return default_data()
        return load()

    def subscribe(self, callback) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def save(self) -> None:
        if self._path is not None:
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)
        else:
            save(self.data)
        self._notify()

    def update(self, mutator) -> None:
        mutator(self.data)
        self.save()

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb(self.data)
            except Exception:
                pass  # a broken listener must never take down persistence
