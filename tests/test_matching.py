"""
tests/test_matching.py
======================
Unit tests for app.core.matching

Run with:
    python -m unittest tests.test_matching -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.matching import find_station, resolve_band
from app.core.models import ReceivedQSO, Station


def _station(norm_call: str) -> Station:
    s = Station()
    s.callsign = norm_call
    s.normalized_callsign = norm_call
    return s


def _qso(band: str = "", freq_hz: float | None = None) -> ReceivedQSO:
    q = ReceivedQSO()
    q.original_callsign = "ON3VZ"
    q.normalized_callsign = "ON3VZ"
    q.band = band
    q.frequency_hz = freq_hz
    return q


class TestFindStation(unittest.TestCase):

    def setUp(self):
        self.map = {
            "ON3VZ":  _station("ON3VZ"),
            "ON4ABC": _station("ON4ABC"),
        }

    def test_exact_match(self):
        s = find_station("ON3VZ", self.map)
        self.assertIsNotNone(s)
        self.assertEqual(s.normalized_callsign, "ON3VZ")

    def test_no_match_returns_none(self):
        self.assertIsNone(find_station("ON9ZZZ", self.map))

    def test_strict_no_soft_match(self):
        # Station stored as ON3VZ, QSO arrives as ON3VZ
        # With strict=True, soft path is skipped entirely
        self.assertIsNotNone(find_station("ON3VZ", self.map, strict=True))

    def test_strict_no_match_for_different_call(self):
        self.assertIsNone(find_station("ON9ZZZ", self.map, strict=True))

    def test_empty_station_map(self):
        self.assertIsNone(find_station("ON3VZ", {}))

    def test_case_already_normalised(self):
        # station_map keys are normalised; QSO call should also be normalised before lookup
        self.assertIsNotNone(find_station("ON3VZ", self.map))

    def test_soft_match_when_map_has_base_call(self):
        """Non-strict: QSO with /P matches base callsign in map."""
        from app.core.callsign import normalize
        norm_qso = normalize("ON3VZ/P", strict=False)  # → "ON3VZ"
        s = find_station(norm_qso, self.map, strict=False)
        self.assertIsNotNone(s)
        self.assertEqual(s.normalized_callsign, "ON3VZ")


class TestResolveBand(unittest.TestCase):

    def test_band_already_set_n1mm_format(self):
        q = _qso(band="40M")
        self.assertEqual(resolve_band(q), "40m")

    def test_band_already_set_lowercase(self):
        q = _qso(band="40m")
        self.assertEqual(resolve_band(q), "40m")

    def test_band_from_frequency_hz(self):
        # 7.030 MHz = 7_030_000 Hz → 40m
        q = _qso(freq_hz=7_030_000.0)
        self.assertEqual(resolve_band(q), "40m")

    def test_band_preferred_over_frequency(self):
        # Band set correctly; frequency would give a different band
        q = _qso(band="40m", freq_hz=14_200_000.0)
        self.assertEqual(resolve_band(q), "40m")

    def test_unknown_band_falls_back_to_frequency(self):
        q = _qso(band="BOGUS", freq_hz=7_030_000.0)
        self.assertEqual(resolve_band(q), "40m")

    def test_no_band_no_frequency_returns_none(self):
        q = _qso()
        self.assertIsNone(resolve_band(q))

    def test_out_of_band_frequency_returns_none(self):
        q = _qso(freq_hz=5_000_000.0)  # no amateur band at 5 MHz
        self.assertIsNone(resolve_band(q))

    def test_2m_band(self):
        q = _qso(band="2M")
        self.assertEqual(resolve_band(q), "2m")

    def test_70cm_band(self):
        q = _qso(freq_hz=432_000_000.0)
        self.assertEqual(resolve_band(q), "70cm")


if __name__ == "__main__":
    unittest.main()
