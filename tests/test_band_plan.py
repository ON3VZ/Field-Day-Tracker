"""
tests/test_band_plan.py
=======================
Unit tests for app.core.band_plan

Run with:
    python -m pytest tests/test_band_plan.py -v
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.band_plan import (
    get_band,
    band_from_n1mm_name,
    band_from_frequency_hz,
    band_from_n1mm_freq_field,
    validate_selected_bands,
    ordered_band_names,
    ALL_BAND_NAMES,
    DEFAULT_SELECTED_BANDS,
)


class TestGetBand(unittest.TestCase):

    def test_known_band(self):
        b = get_band("40m")
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "40m")

    def test_case_insensitive(self):
        self.assertIsNotNone(get_band("40M"))
        self.assertIsNotNone(get_band("40m"))

    def test_unknown_band(self):
        self.assertIsNone(get_band("99m"))

    def test_all_bands_retrievable(self):
        for name in ALL_BAND_NAMES:
            self.assertIsNotNone(get_band(name), f"Band {name} not found")


class TestBandFromN1mmName(unittest.TestCase):

    def test_40m(self):
        b = band_from_n1mm_name("40M")
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "40m")

    def test_2m(self):
        b = band_from_n1mm_name("2M")
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "2m")

    def test_70cm(self):
        b = band_from_n1mm_name("70CM")
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "70cm")

    def test_case_insensitive(self):
        self.assertIsNotNone(band_from_n1mm_name("40m"))

    def test_unknown(self):
        self.assertIsNone(band_from_n1mm_name("99M"))


class TestBandFromFrequencyHz(unittest.TestCase):
    """band_from_frequency_hz() — input in Hz."""

    def test_40m_frequency(self):
        # 7.030 MHz = 7_030_000 Hz
        b = band_from_frequency_hz(7_030_000)
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "40m")

    def test_20m_frequency(self):
        b = band_from_frequency_hz(14_200_000)
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "20m")

    def test_2m_frequency(self):
        b = band_from_frequency_hz(145_500_000)
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "2m")

    def test_out_of_band(self):
        self.assertIsNone(band_from_frequency_hz(5_000_000))

    def test_lower_edge_40m(self):
        # Exactly 7.000 MHz
        b = band_from_frequency_hz(7_000_000)
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "40m")

    def test_upper_edge_40m(self):
        # Exactly 7.200 MHz
        b = band_from_frequency_hz(7_200_000)
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "40m")


class TestBandFromN1mmFreqField(unittest.TestCase):
    """band_from_n1mm_freq_field() — N1MM uses 10-Hz units."""

    def test_40m_n1mm_value(self):
        # N1MM value 703000 = 703000 × 10 Hz = 7_030_000 Hz = 7.030 MHz
        b = band_from_n1mm_freq_field(703000)
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "40m")

    def test_string_input(self):
        b = band_from_n1mm_freq_field("703000")
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "40m")

    def test_invalid_input(self):
        self.assertIsNone(band_from_n1mm_freq_field("notanumber"))

    def test_none_input(self):
        self.assertIsNone(band_from_n1mm_freq_field(None))

    def test_20m(self):
        # 14.200 MHz → 1420000 in N1MM units
        b = band_from_n1mm_freq_field(1_420_000)
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "20m")


class TestValidateSelectedBands(unittest.TestCase):

    def test_all_valid(self):
        valid, invalid = validate_selected_bands(["40m", "80m", "20m"])
        self.assertEqual(set(valid), {"40m", "80m", "20m"})
        self.assertEqual(invalid, [])

    def test_some_invalid(self):
        valid, invalid = validate_selected_bands(["40m", "99m", "FAKE"])
        self.assertIn("40m", valid)
        self.assertIn("99m", invalid)
        self.assertIn("FAKE", invalid)

    def test_case_normalised(self):
        valid, invalid = validate_selected_bands(["40M", "80M"])
        self.assertIn("40m", valid)
        self.assertIn("80m", valid)
        self.assertEqual(invalid, [])

    def test_empty(self):
        valid, invalid = validate_selected_bands([])
        self.assertEqual(valid, [])
        self.assertEqual(invalid, [])


class TestOrderedBandNames(unittest.TestCase):

    def test_order_preserved(self):
        # Input in wrong order → output in band-plan order
        result = ordered_band_names(["20m", "160m", "40m"])
        self.assertEqual(result, ["160m", "40m", "20m"])

    def test_single_band(self):
        self.assertEqual(ordered_band_names(["6m"]), ["6m"])

    def test_default_bands_ordered(self):
        result = ordered_band_names(list(DEFAULT_SELECTED_BANDS))
        self.assertEqual(result, ["160m", "80m", "40m"])


if __name__ == "__main__":
    unittest.main()
