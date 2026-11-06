import json

from focusquest.core.storage import DataStore, default_data


def test_default_data_shape():
    d = default_data()
    assert d["schema_version"] == 1
    assert d["settings"]["focus_minutes"] == 25
    assert d["xp"] == 0 and d["badges"] == [] and d["days"] == {}


def test_roundtrip_with_tmp_file(tmp_path):
    target = tmp_path / "data.json"
    store = DataStore(target)
    store.data["xp"] = 42
    store.data["settings"]["focus_minutes"] = 30
    store.save()

    reopened = DataStore(target)
    assert reopened.data["xp"] == 42
    assert reopened.data["settings"]["focus_minutes"] == 30


def test_corrupt_file_recovers_from_backup(tmp_path):
    target = tmp_path / "data.json"
    bak = tmp_path / "data.json.bak"
    good = default_data()
    good["xp"] = 777
    bak.write_text(json.dumps(good), encoding="utf-8")
    target.write_text("{ not json !!!", encoding="utf-8")

    store = DataStore(target)
    assert store.data["xp"] == 777


def test_merge_defaults_fills_missing_keys(tmp_path):
    target = tmp_path / "data.json"
    target.write_text(json.dumps({"xp": 5, "settings": {"focus_minutes": 50}}),
                      encoding="utf-8")
    store = DataStore(target)
    assert store.data["xp"] == 5
    assert store.data["settings"]["focus_minutes"] == 50
    assert store.data["settings"]["break_minutes"] == 5  # filled from defaults
    assert store.data["sessions"] == []
