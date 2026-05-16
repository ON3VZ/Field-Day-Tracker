"""
tests/test_models.py
====================
Unit tests for app.core.models

Run with:
    python -m pytest tests/test_models.py -v
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.models import (
    AppSettings, FieldDay, Station, ReceivedQSO, Override, SyncResult
)
from app.core.status import Status


class TestFieldDayPeriod(unittest.TestCase):

    def _make_fd(self, start_offset_hours=0, end_offset_hours=24):
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=start_offset_hours)
        end = now + timedelta(hours=end_offset_hours)
        fd = FieldDay()
        fd.start_utc = start.isoformat()
        fd.end_utc = end.isoformat()
        return fd, start, end

    def test_valid_period(self):
        fd, _, _ = self._make_fd(0, 24)
        self.assertTrue(fd.is_valid_period())

    def test_invalid_period_end_before_start(self):
        fd, _, _ = self._make_fd(0, -1)
        self.assertFalse(fd.is_valid_period())

    def test_invalid_period_equal(self):
        now = datetime.now(timezone.utc).isoformat()
        fd = FieldDay()
        fd.start_utc = now
        fd.end_utc = now
        self.assertFalse(fd.is_valid_period())

    def test_qso_in_period(self):
        fd, start, end = self._make_fd(0, 24)
        mid = start + timedelta(hours=12)
        self.assertTrue(fd.qso_in_period(mid.isoformat()))

    def test_qso_before_period(self):
        fd, start, _ = self._make_fd(0, 24)
        before = start - timedelta(hours=1)
        self.assertFalse(fd.qso_in_period(before.isoformat()))

    def test_qso_after_period(self):
        fd, _, end = self._make_fd(0, 24)
        after = end + timedelta(hours=1)
        self.assertFalse(fd.qso_in_period(after.isoformat()))

    def test_qso_at_start_boundary(self):
        fd, start, _ = self._make_fd(0, 24)
        self.assertTrue(fd.qso_in_period(start.isoformat()))

    def test_qso_at_end_boundary(self):
        fd, _, end = self._make_fd(0, 24)
        self.assertTrue(fd.qso_in_period(end.isoformat()))

    def test_qso_invalid_timestamp(self):
        fd, _, _ = self._make_fd(0, 24)
        self.assertFalse(fd.qso_in_period("not-a-date"))

    def test_empty_period(self):
        fd = FieldDay()
        self.assertFalse(fd.qso_in_period(datetime.now(timezone.utc).isoformat()))


class TestFieldDaySerialisation(unittest.TestCase):

    def test_round_trip(self):
        fd = FieldDay()
        fd.name = "TestFD2025"
        fd.location = "Ghent"
        fd.event_callsign = "ON3VZ"
        fd.selected_bands = ["40m", "80m"]
        d = fd.to_dict()
        fd2 = FieldDay.from_dict(d)
        self.assertEqual(fd2.name, "TestFD2025")
        self.assertEqual(fd2.location, "Ghent")
        self.assertEqual(fd2.selected_bands, ["40m", "80m"])

    def test_from_empty_dict(self):
        fd = FieldDay.from_dict({})
        self.assertEqual(fd.name, "")
        self.assertFalse(fd.is_valid_period())


class TestStationSerialisation(unittest.TestCase):

    def test_round_trip(self):
        s = Station()
        s.callsign = "ON3VZ/P"
        s.normalized_callsign = "ON3VZ"
        s.name = "Cornelis"
        s.club = "WLD"
        s.source = "csv"
        d = s.to_dict()
        s2 = Station.from_dict(d)
        self.assertEqual(s2.callsign, "ON3VZ/P")
        self.assertEqual(s2.normalized_callsign, "ON3VZ")
        self.assertEqual(s2.name, "Cornelis")


class TestReceivedQSOSerialisation(unittest.TestCase):

    def test_round_trip(self):
        q = ReceivedQSO()
        q.original_callsign = "ON3VZ/P"
        q.normalized_callsign = "ON3VZ"
        q.band = "40m"
        q.frequency_hz = 7_030_000.0
        q.mode = "CW"
        q.timestamp_utc = "2025-06-21T10:00:00+00:00"
        d = q.to_dict()
        q2 = ReceivedQSO.from_dict(d)
        self.assertEqual(q2.original_callsign, "ON3VZ/P")
        self.assertEqual(q2.band, "40m")
        self.assertAlmostEqual(q2.frequency_hz, 7_030_000.0)


class TestOverride(unittest.TestCase):

    def test_key(self):
        o = Override()
        o.normalized_callsign = "ON3VZ"
        o.band = "40m"
        self.assertEqual(o.key, ("ON3VZ", "40m"))

    def test_round_trip(self):
        o = Override()
        o.normalized_callsign = "ON3VZ"
        o.band = "160m"
        o.status = Status.MANUAL_WORKED.value
        d = o.to_dict()
        o2 = Override.from_dict(d)
        self.assertEqual(o2.key, ("ON3VZ", "160m"))
        self.assertEqual(o2.status, Status.MANUAL_WORKED.value)


class TestAppSettings(unittest.TestCase):

    def test_defaults(self):
        s = AppSettings()
        self.assertEqual(s.ui_language, "en")
        self.assertEqual(s.n1mm_udp_port, 12060)
        self.assertFalse(s.strict_callsign_matching)

    def test_round_trip(self):
        s = AppSettings()
        s.ui_language = "nl"
        s.strict_callsign_matching = True
        s.last_active_fieldday = "MyFD2025"
        d = s.to_dict()
        s2 = AppSettings.from_dict(d)
        self.assertEqual(s2.ui_language, "nl")
        self.assertTrue(s2.strict_callsign_matching)
        self.assertEqual(s2.last_active_fieldday, "MyFD2025")


if __name__ == "__main__":
    unittest.main()
