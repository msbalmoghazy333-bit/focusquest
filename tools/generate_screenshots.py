"""Generate README screenshots by rendering the UI offscreen."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from focusquest.app import create_app
from focusquest.core import storage
from focusquest.core.storage import DataStore
from focusquest.ui.main_window import MainWindow

OUT = ROOT / "assets" / "screenshots"


def main() -> None:
    tmp = Path(tempfile.mkdtemp()) / "data.json"
    data = storage.default_data()
    data["xp"] = 145
    data["badges"] = ["first_session", "no_distraction"]
    for day, mins in [("2026-11-06", 75), ("2026-11-05", 50),
                      ("2026-11-04", 25), ("2026-11-03", 90)]:
        data["days"][day] = {"focus_sec": mins * 60,
                             "sessions_done": mins // 25 or 1,
                             "sessions_aborted": 0, "violations": 0}
    data["sessions"] = [{"start": "2026-11-06T10:00:00", "worked_sec": 1500,
                         "planned_sec": 1500, "completed": True,
                         "task": "حل ٥ مسائل جبر", "violations": 0}]
    tmp.write_text(json.dumps(data), encoding="utf-8")

    app = create_app(["screenshot"])
    store = DataStore(tmp)
    window = MainWindow(store)
    window.resize(900, 700)
    window.show()
    app.processEvents()
    OUT.mkdir(parents=True, exist_ok=True)
    window._tabs.setCurrentIndex(0)
    app.processEvents()
    window.grab().save(str(OUT / "session.png"))
    window._tabs.setCurrentIndex(1)
    app.processEvents()
    window.grab().save(str(OUT / "stats.png"))
    window._tabs.setCurrentIndex(2)
    app.processEvents()
    window.grab().save(str(OUT / "settings.png"))
    print("screenshots saved to", OUT)


if __name__ == "__main__":
    main()
