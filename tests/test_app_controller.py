"""
tests/test_app_controller.py
=============================
Unit tests for app.app_controller.AppController

Tests all controller logic without any Tkinter/GUI dependencies.

Run with:
    python -m unittest tests.test_app_controller -v
"""

import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.app_controller import AppController
from app.core.models import AppSettings, FieldDay, Station, Override
from app.core.status import Status


def _utc(offset_h: float = 0) -> str:
    base = datetime(2025, 6, 21, 8, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(hours=offset_h)).isoformat()


def _make_fd(name: str = "TestFD") -> FieldDay:
    fd = FieldDay()
    fd.name = name
    fd.location = "Test Location"
    fd.event_callsign = "ON0TEST"
    fd.start_utc = _utc(-1)
    fd.end_utc = _utc(23)
    fd.selected_bands = ["40m", "80m"]
    return fd


def _make_station(call: str, source: str = "csv") -> Station:
    s = Station()
    s.callsign = call
    s.normalized_callsign = call.upper()
    s.source = source
    return s


class TestAppControllerBasic(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ctrl = AppController(self.tmp)
        # Don't call startup() — that starts UDP listener
        # Load settings manually for tests
        self.ctrl._settings = AppSettings()

    def tearDown(self):
        # Stop listener if started
        if self.ctrl._listener:
            self.ctrl._listener.stop()
        shutil.rmtree(self.tmp)

    def test_no_active_fieldday_initially(self):
        self.assertFalse(self.ctrl.has_active_fieldday)
        self.assertIsNone(self.ctrl.fieldday)

    def test_create_fieldday(self):
        fd = _make_fd("FD2025")
        self.ctrl.create_fieldday(fd)
        self.assertTrue(self.ctrl.has_active_fieldday)
        self.assertEqual(self.ctrl.fieldday.name, "FD2025")

    def test_create_fieldday_invalid_name_raises(self):
        fd = _make_fd("invalid name!")
        with self.assertRaises(ValueError):
            self.ctrl.create_fieldday(fd)

    def test_create_duplicate_fieldday_raises(self):
        fd = _make_fd("UniqueTest")
        self.ctrl.create_fieldday(fd)
        with self.assertRaises(ValueError):
            self.ctrl.create_fieldday(_make_fd("UniqueTest"))

    def test_list_fielddays_empty(self):
        self.assertEqual(self.ctrl.list_fielddays(), [])

    def test_list_fielddays_after_create(self):
        self.ctrl.create_fieldday(_make_fd("FD_A"))
        self.ctrl.create_fieldday(_make_fd("FD_B"))
        names = self.ctrl.list_fielddays()
        self.assertIn("FD_A", names)
        self.assertIn("FD_B", names)

    def test_open_fieldday(self):
        self.ctrl.create_fieldday(_make_fd("OpenTest"))
        # Create a second controller pointing to same root
        ctrl2 = AppController(self.tmp)
        ctrl2._settings = AppSettings()
        result = ctrl2.open_fieldday("OpenTest")
        self.assertTrue(result)
        self.assertEqual(ctrl2.fieldday.name, "OpenTest")

    def test_open_nonexistent_fieldday_returns_false(self):
        result = self.ctrl.open_fieldday("DoesNotExist")
        self.assertFalse(result)

    def test_last_active_persisted_on_create(self):
        self.ctrl.create_fieldday(_make_fd("Persist"))
        self.assertEqual(self.ctrl.settings.last_active_fieldday, "Persist")

    def test_stations_initially_empty(self):
        self.ctrl.create_fieldday(_make_fd())
        self.assertEqual(self.ctrl.stations, [])

    def test_add_station_manual(self):
        self.ctrl.create_fieldday(_make_fd())
        s = _make_station("ON3VZ", "manual")
        result = self.ctrl.add_station_manual(s)
        self.assertTrue(result)
        self.assertEqual(len(self.ctrl.stations), 1)

    def test_add_duplicate_station_returns_false(self):
        self.ctrl.create_fieldday(_make_fd())
        s = _make_station("ON3VZ", "manual")
        self.ctrl.add_station_manual(s)
        result = self.ctrl.add_station_manual(_make_station("ON3VZ", "manual"))
        self.assertFalse(result)
        self.assertEqual(len(self.ctrl.stations), 1)

    def test_update_station_remarks(self):
        self.ctrl.create_fieldday(_make_fd())
        s = _make_station("ON3VZ", "manual")
        self.ctrl.add_station_manual(s)
        self.ctrl.update_station_remarks("ON3VZ", "Test remark")
        self.assertEqual(self.ctrl.stations[0].remarks, "Test remark")


class TestAppControllerSync(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ctrl = AppController(self.tmp)
        self.ctrl._settings = AppSettings()
        self.ctrl.create_fieldday(_make_fd("SyncTest"))
        # Add stations directly
        for call in ["ON3VZ", "ON4ABC"]:
            self.ctrl.add_station_manual(_make_station(call, "manual"))

    def tearDown(self):
        if self.ctrl._listener:
            self.ctrl._listener.stop()
        shutil.rmtree(self.tmp)

    def test_recalculate_empty_qsos(self):
        result = self.ctrl.recalculate()
        self.assertEqual(result.worked_combinations, 0)
        self.assertEqual(result.unworked_combinations, 4)  # 2 stations × 2 bands

    def test_recalculate_after_qso(self):
        from app.core.models import ReceivedQSO
        q = ReceivedQSO()
        q.original_callsign = "ON3VZ"
        q.normalized_callsign = "ON3VZ"
        q.band = "40m"
        q.timestamp_utc = _utc(5)
        q.n1mm_id = "test-001"
        self.ctrl._qsos.append(q)
        result = self.ctrl.recalculate()
        self.assertEqual(result.worked_combinations, 1)

    def test_override_wins_over_qso(self):
        from app.core.models import ReceivedQSO
        q = ReceivedQSO()
        q.original_callsign = "ON3VZ"
        q.normalized_callsign = "ON3VZ"
        q.band = "40m"
        q.timestamp_utc = _utc(5)
        q.n1mm_id = "test-002"
        self.ctrl._qsos.append(q)
        # Override says not worked
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_NOT_WORKED)
        matrix = self.ctrl.matrix
        self.assertEqual(
            matrix[("ON3VZ", "40m")].status,
            Status.MANUAL_NOT_WORKED,
        )

    def test_clear_override(self):
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_WORKED)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.MANUAL_WORKED,
        )
        self.ctrl.clear_override("ON3VZ", "40m")
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.NOT_WORKED,
        )

    def test_get_summary(self):
        summary = self.ctrl.get_summary()
        self.assertEqual(summary["total_stations"], 2)
        self.assertEqual(summary["total_bands"], 2)
        self.assertEqual(summary["total_combinations"], 4)
        self.assertEqual(summary["worked"], 0)
        self.assertEqual(summary["unworked"], 4)

    def test_get_station_statistics(self):
        stats = self.ctrl.get_station_statistics()
        self.assertEqual(stats["not_worked"], 2)
        self.assertEqual(stats["fully_worked"], 0)
        self.assertEqual(stats["partially_worked"], 0)


class TestAppControllerCSVImport(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ctrl = AppController(self.tmp)
        self.ctrl._settings = AppSettings()
        self.ctrl.create_fieldday(_make_fd("CSVTest"))

    def tearDown(self):
        if self.ctrl._listener:
            self.ctrl._listener.stop()
        shutil.rmtree(self.tmp)

    def _write_csv(self, content: str) -> Path:
        p = self.tmp / "test.csv"
        p.write_text(content, encoding="utf-8")
        return p

    def test_import_csv_success(self):
        path = self._write_csv("callsign,name\nON3VZ,Cornelis\nON4ABC,\n")
        result = self.ctrl.import_csv(path)
        self.assertTrue(result.success)
        self.assertEqual(len(self.ctrl.stations), 2)

    def test_import_csv_invalid(self):
        path = self._write_csv("name,club\nCornélis,WLD\n")
        result = self.ctrl.import_csv(path)
        self.assertFalse(result.success)
        # Stations unchanged
        self.assertEqual(len(self.ctrl.stations), 0)

    def test_apply_csv_removals(self):
        path = self._write_csv("callsign\nON3VZ\nON4ABC\n")
        self.ctrl.import_csv(path)
        self.assertEqual(len(self.ctrl.stations), 2)
        self.ctrl.apply_csv_removals(["ON4ABC"])
        self.assertEqual(len(self.ctrl.stations), 1)
        self.assertEqual(self.ctrl.stations[0].normalized_callsign, "ON3VZ")


class TestAppControllerObservers(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ctrl = AppController(self.tmp)
        self.ctrl._settings = AppSettings()

    def tearDown(self):
        if self.ctrl._listener:
            self.ctrl._listener.stop()
        shutil.rmtree(self.tmp)

    def test_fieldday_changed_callback_called(self):
        calls = []
        self.ctrl.register_on_fieldday_changed(lambda: calls.append(1))
        self.ctrl.create_fieldday(_make_fd("ObsTest"))
        self.assertGreater(len(calls), 0)

    def test_matrix_changed_callback_called_on_sync(self):
        self.ctrl.create_fieldday(_make_fd("MatTest"))
        calls = []
        self.ctrl.register_on_matrix_changed(lambda: calls.append(1))
        self.ctrl.recalculate()
        self.assertGreater(len(calls), 0)

    def test_multiple_callbacks(self):
        calls_a, calls_b = [], []
        self.ctrl.register_on_matrix_changed(lambda: calls_a.append(1))
        self.ctrl.register_on_matrix_changed(lambda: calls_b.append(1))
        self.ctrl.create_fieldday(_make_fd("MultiObs"))
        self.assertGreater(len(calls_a), 0)
        self.assertGreater(len(calls_b), 0)


if __name__ == "__main__":
    unittest.main()
