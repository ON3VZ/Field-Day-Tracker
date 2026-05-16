"""
tests/test_storage.py
=====================
Unit tests for app.storage.json_store and app.storage.fieldday_repository

Run with:
    python -m unittest tests.test_storage -v
"""

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.json_store import (
    read_json,
    read_json_dict,
    read_json_list,
    write_json,
    ensure_dir,
)
from app.storage.fieldday_repository import (
    AppSettingsRepository,
    FieldDayRepository,
    is_valid_fieldday_name,
)
from app.core.models import (
    AppSettings, FieldDay, Station, ReceivedQSO, Override
)
from app.core.status import Status


class TestJsonStore(unittest.TestCase):
    """Tests for json_store atomic read/write."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_write_and_read_dict(self):
        path = self.tmp / "test.json"
        data = {"key": "value", "number": 42}
        write_json(path, data)
        result = read_json(path)
        self.assertEqual(result, data)

    def test_write_and_read_list(self):
        path = self.tmp / "list.json"
        data = [1, 2, 3, {"a": "b"}]
        write_json(path, data)
        result = read_json_list(path)
        self.assertEqual(result, data)

    def test_read_missing_file_returns_none(self):
        result = read_json(self.tmp / "nonexistent.json")
        self.assertIsNone(result)

    def test_read_dict_missing_returns_empty(self):
        result = read_json_dict(self.tmp / "nonexistent.json")
        self.assertEqual(result, {})

    def test_read_list_missing_returns_empty(self):
        result = read_json_list(self.tmp / "nonexistent.json")
        self.assertEqual(result, [])

    def test_read_corrupt_json_returns_none(self):
        path = self.tmp / "corrupt.json"
        path.write_text("{ this is not json }", encoding="utf-8")
        result = read_json(path)
        self.assertIsNone(result)

    def test_read_list_from_dict_file_returns_empty(self):
        path = self.tmp / "dict.json"
        write_json(path, {"key": "val"})
        result = read_json_list(path)
        self.assertEqual(result, [])

    def test_atomic_write_creates_parent_dirs(self):
        path = self.tmp / "a" / "b" / "c" / "test.json"
        write_json(path, {"x": 1})
        self.assertTrue(path.exists())

    def test_atomic_write_unicode(self):
        path = self.tmp / "unicode.json"
        data = {"name": "Ünïcödé strïng 日本語"}
        write_json(path, data)
        result = read_json(path)
        self.assertEqual(result["name"], data["name"])

    def test_atomic_write_no_temp_file_left_behind(self):
        path = self.tmp / "clean.json"
        write_json(path, {"ok": True})
        tmp_files = list(self.tmp.glob("*.tmp.json"))
        self.assertEqual(tmp_files, [], "Temp files should be cleaned up")

    def test_overwrite_existing_file(self):
        path = self.tmp / "overwrite.json"
        write_json(path, {"v": 1})
        write_json(path, {"v": 2})
        result = read_json(path)
        self.assertEqual(result["v"], 2)

    def test_ensure_dir_creates_nested(self):
        nested = self.tmp / "x" / "y" / "z"
        ensure_dir(nested)
        self.assertTrue(nested.is_dir())

    def test_ensure_dir_existing_is_noop(self):
        ensure_dir(self.tmp)  # already exists — should not raise
        self.assertTrue(self.tmp.is_dir())


class TestIsValidFielddayName(unittest.TestCase):

    def test_valid_names(self):
        for name in ["FD2025", "field_day_2025", "test-fd", "A1"]:
            self.assertTrue(is_valid_fieldday_name(name), f"Should be valid: {name}")

    def test_invalid_names(self):
        for name in ["", "with space", "has/slash", "has.dot", "has@at"]:
            self.assertFalse(is_valid_fieldday_name(name), f"Should be invalid: {name}")


class TestAppSettingsRepository(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = AppSettingsRepository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_load_defaults_when_missing(self):
        settings = self.repo.load()
        self.assertEqual(settings.ui_language, "en")
        self.assertEqual(settings.n1mm_udp_port, 12060)

    def test_save_and_reload(self):
        settings = AppSettings()
        settings.ui_language = "nl"
        settings.strict_callsign_matching = True
        settings.last_active_fieldday = "MyFD2025"
        self.repo.save(settings)

        loaded = self.repo.load()
        self.assertEqual(loaded.ui_language, "nl")
        self.assertTrue(loaded.strict_callsign_matching)
        self.assertEqual(loaded.last_active_fieldday, "MyFD2025")

    def test_set_last_active(self):
        settings = self.repo.load()
        self.repo.set_last_active("TestFD", settings)
        loaded = self.repo.load()
        self.assertEqual(loaded.last_active_fieldday, "TestFD")

    def test_set_last_active_none(self):
        settings = self.repo.load()
        self.repo.set_last_active(None, settings)
        loaded = self.repo.load()
        self.assertIsNone(loaded.last_active_fieldday)


class TestFieldDayRepository(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = FieldDayRepository(self.tmp, "TestFD2025")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    # -- Setup --

    def test_folder_created(self):
        self.assertTrue(self.repo.folder.is_dir())

    def test_exports_folder_created(self):
        self.assertTrue(self.repo.exports_folder.is_dir())

    def test_invalid_name_raises(self):
        with self.assertRaises(ValueError):
            FieldDayRepository(self.tmp, "invalid name!")

    # -- FieldDay metadata --

    def test_load_missing_fieldday_returns_skeleton(self):
        fd = self.repo.load_fieldday()
        self.assertEqual(fd.name, "TestFD2025")

    def test_save_and_load_fieldday(self):
        fd = FieldDay()
        fd.name = "TestFD2025"
        fd.location = "Ghent"
        fd.event_callsign = "ON3VZ"
        fd.selected_bands = ["40m", "80m"]
        now = datetime.now(timezone.utc)
        fd.start_utc = now.isoformat()
        fd.end_utc = (now + timedelta(hours=24)).isoformat()
        self.repo.save_fieldday(fd)

        loaded = self.repo.load_fieldday()
        self.assertEqual(loaded.location, "Ghent")
        self.assertEqual(loaded.event_callsign, "ON3VZ")
        self.assertEqual(loaded.selected_bands, ["40m", "80m"])
        self.assertTrue(loaded.is_valid_period())

    def test_save_fieldday_updates_updated_at(self):
        fd = self.repo.load_fieldday()
        original = fd.updated_at
        import time; time.sleep(0.01)
        self.repo.save_fieldday(fd)
        loaded = self.repo.load_fieldday()
        self.assertGreaterEqual(loaded.updated_at, original)

    # -- Stations --

    def test_load_missing_stations_returns_empty(self):
        stations = self.repo.load_stations()
        self.assertEqual(stations, [])

    def test_save_and_load_stations(self):
        s1 = Station()
        s1.callsign = "ON3VZ"
        s1.normalized_callsign = "ON3VZ"
        s1.name = "Cornelis"
        s1.source = "csv"
        s2 = Station()
        s2.callsign = "ON4ABC"
        s2.normalized_callsign = "ON4ABC"
        s2.source = "manual"

        self.repo.save_stations([s1, s2])
        loaded = self.repo.load_stations()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].normalized_callsign, "ON3VZ")
        self.assertEqual(loaded[1].source, "manual")

    def test_add_station_no_duplicate(self):
        s1 = Station()
        s1.normalized_callsign = "ON3VZ"
        stations = [s1]
        s2 = Station()
        s2.normalized_callsign = "ON3VZ"  # duplicate
        result = self.repo.add_station(s2, stations)
        self.assertEqual(len(result), 1)

    def test_add_station_new(self):
        s1 = Station()
        s1.normalized_callsign = "ON3VZ"
        s2 = Station()
        s2.normalized_callsign = "ON4ABC"
        result = self.repo.add_station(s2, [s1])
        self.assertEqual(len(result), 2)

    def test_station_map(self):
        s1 = Station(); s1.normalized_callsign = "ON3VZ"
        s2 = Station(); s2.normalized_callsign = "ON4ABC"
        m = self.repo.station_map([s1, s2])
        self.assertIn("ON3VZ", m)
        self.assertIn("ON4ABC", m)

    # -- QSOs --

    def test_load_missing_qsos_returns_empty(self):
        self.assertEqual(self.repo.load_qsos(), [])

    def test_save_and_load_qsos(self):
        q = ReceivedQSO()
        q.original_callsign = "ON3VZ/P"
        q.normalized_callsign = "ON3VZ"
        q.band = "40m"
        q.timestamp_utc = "2025-06-21T10:00:00+00:00"
        q.n1mm_id = "12345"
        self.repo.save_qsos([q])

        loaded = self.repo.load_qsos()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].normalized_callsign, "ON3VZ")
        self.assertEqual(loaded[0].n1mm_id, "12345")

    def test_append_qso_deduplication(self):
        q1 = ReceivedQSO(); q1.n1mm_id = "111"; q1.band = "40m"
        q2 = ReceivedQSO(); q2.n1mm_id = "111"; q2.band = "40m"  # duplicate
        q3 = ReceivedQSO(); q3.n1mm_id = "222"; q3.band = "80m"

        existing = [q1]
        existing = self.repo.append_qso(q2, existing)  # duplicate → ignored
        self.assertEqual(len(existing), 1)
        existing = self.repo.append_qso(q3, existing)  # new → added
        self.assertEqual(len(existing), 2)

    def test_append_qso_no_id(self):
        """QSOs without n1mm_id are always appended (no dedup possible)."""
        q1 = ReceivedQSO(); q1.n1mm_id = ""; q1.band = "40m"
        q2 = ReceivedQSO(); q2.n1mm_id = ""; q2.band = "40m"
        existing = self.repo.append_qso(q1, [])
        existing = self.repo.append_qso(q2, existing)
        self.assertEqual(len(existing), 2)

    # -- Overrides --

    def test_load_missing_overrides_returns_empty(self):
        self.assertEqual(self.repo.load_overrides(), {})

    def test_save_and_load_overrides(self):
        o = Override()
        o.normalized_callsign = "ON3VZ"
        o.band = "40m"
        o.status = Status.MANUAL_WORKED.value

        overrides = {o.key: o}
        self.repo.save_overrides(overrides)

        loaded = self.repo.load_overrides()
        self.assertIn(("ON3VZ", "40m"), loaded)
        self.assertEqual(loaded[("ON3VZ", "40m")].status, Status.MANUAL_WORKED.value)

    def test_set_override(self):
        o = Override()
        o.normalized_callsign = "ON3VZ"
        o.band = "160m"
        o.status = Status.MANUAL_NOT_WORKED.value
        overrides = {}
        overrides = self.repo.set_override(overrides, o)
        self.assertIn(("ON3VZ", "160m"), overrides)

    def test_clear_override(self):
        o = Override()
        o.normalized_callsign = "ON3VZ"
        o.band = "40m"
        o.status = Status.MANUAL_WORKED.value
        overrides = {o.key: o}
        overrides = self.repo.clear_override(overrides, "ON3VZ", "40m")
        self.assertNotIn(("ON3VZ", "40m"), overrides)

    def test_clear_nonexistent_override_is_noop(self):
        overrides = {}
        result = self.repo.clear_override(overrides, "ON3VZ", "40m")
        self.assertEqual(result, {})

    # -- Sync log --

    def test_append_and_load_sync_log(self):
        self.repo.append_sync_log({"event": "sync", "worked": 5})
        self.repo.append_sync_log({"event": "error", "msg": "test"})
        log = self.repo.load_sync_log()
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["event"], "sync")

    def test_sync_log_capped_at_100(self):
        for i in range(110):
            self.repo.append_sync_log({"i": i})
        log = self.repo.load_sync_log()
        self.assertLessEqual(len(log), 100)
        # Most recent entries are kept
        self.assertEqual(log[-1]["i"], 109)

    # -- Discovery --

    def test_list_fielddays(self):
        # TestFD2025 already has a folder; save metadata so it's discovered
        fd = FieldDay(); fd.name = "TestFD2025"
        self.repo.save_fieldday(fd)

        # Create a second field day
        repo2 = FieldDayRepository(self.tmp, "AnotherFD")
        fd2 = FieldDay(); fd2.name = "AnotherFD"
        repo2.save_fieldday(fd2)

        names = FieldDayRepository.list_fielddays(self.tmp)
        self.assertIn("TestFD2025", names)
        self.assertIn("AnotherFD", names)

    def test_exists_true(self):
        fd = FieldDay(); fd.name = "TestFD2025"
        self.repo.save_fieldday(fd)
        self.assertTrue(FieldDayRepository.exists(self.tmp, "TestFD2025"))

    def test_exists_false(self):
        self.assertFalse(FieldDayRepository.exists(self.tmp, "DoesNotExist"))

    def test_delete_all_data(self):
        fd = FieldDay(); fd.name = "TestFD2025"
        self.repo.save_fieldday(fd)
        self.repo.save_stations([])
        self.repo.delete_all_data()
        self.assertFalse((self.repo.folder / "fieldday.json").exists())


if __name__ == "__main__":
    unittest.main()
