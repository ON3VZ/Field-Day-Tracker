"""
tests/test_callsign.py
======================
Unit tests for app.core.callsign

Run with:
    python -m pytest tests/test_callsign.py -v
or:
    python -m unittest tests.test_callsign -v
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.callsign import normalize, matches, is_valid_callsign


class TestNormalizeNonStrict(unittest.TestCase):
    """normalize() with strict=False (default)."""

    def test_basic_uppercase(self):
        self.assertEqual(normalize("on3vz"), "ON3VZ")

    def test_strip_whitespace(self):
        self.assertEqual(normalize("  ON3VZ  "), "ON3VZ")

    def test_strip_portable(self):
        self.assertEqual(normalize("ON3VZ/P"), "ON3VZ")

    def test_strip_mobile(self):
        self.assertEqual(normalize("ON3VZ/M"), "ON3VZ")

    def test_strip_maritime_mobile(self):
        self.assertEqual(normalize("ON3VZ/MM"), "ON3VZ")

    def test_strip_qrp(self):
        self.assertEqual(normalize("ON3VZ/QRP"), "ON3VZ")

    def test_strip_district_suffix(self):
        self.assertEqual(normalize("W1AW/4"), "W1AW")

    def test_no_strip_dxcc_prefix(self):
        # Slash at position 1 → too short base → no strip
        self.assertEqual(normalize("F/ON3VZ"), "F/ON3VZ")

    def test_empty_string(self):
        self.assertEqual(normalize(""), "")

    def test_whitespace_only(self):
        self.assertEqual(normalize("   "), "")

    def test_no_suffix(self):
        self.assertEqual(normalize("ON3VZ"), "ON3VZ")

    def test_lowercase_suffix(self):
        self.assertEqual(normalize("on3vz/p"), "ON3VZ")

    def test_strip_a_suffix(self):
        self.assertEqual(normalize("ON3VZ/A"), "ON3VZ")


class TestNormalizeStrict(unittest.TestCase):
    """normalize() with strict=True."""

    def test_uppercase_only(self):
        self.assertEqual(normalize("on3vz/p", strict=True), "ON3VZ/P")

    def test_no_suffix_strip(self):
        self.assertEqual(normalize("ON3VZ/M", strict=True), "ON3VZ/M")

    def test_no_district_strip(self):
        self.assertEqual(normalize("W1AW/4", strict=True), "W1AW/4")

    def test_basic(self):
        self.assertEqual(normalize("ON3VZ", strict=True), "ON3VZ")


class TestMatches(unittest.TestCase):
    """matches() function."""

    def test_same_callsign(self):
        self.assertTrue(matches("ON3VZ", "ON3VZ"))

    def test_case_insensitive(self):
        self.assertTrue(matches("on3vz", "ON3VZ"))

    def test_portable_matches_base_nonstrict(self):
        self.assertTrue(matches("ON3VZ", "ON3VZ/P"))

    def test_portable_no_match_strict(self):
        self.assertFalse(matches("ON3VZ", "ON3VZ/P", strict=True))

    def test_different_calls(self):
        self.assertFalse(matches("ON3VZ", "ON4ABC"))

    def test_both_portable_nonstrict(self):
        self.assertTrue(matches("ON3VZ/P", "ON3VZ/M"))

    def test_both_portable_strict(self):
        self.assertFalse(matches("ON3VZ/P", "ON3VZ/M", strict=True))

    def test_qrp_matches_base(self):
        self.assertTrue(matches("ON3VZ", "ON3VZ/QRP"))


class TestIsValidCallsign(unittest.TestCase):
    """is_valid_callsign() validation."""

    def test_valid_basic(self):
        self.assertTrue(is_valid_callsign("ON3VZ"))

    def test_valid_with_suffix(self):
        self.assertTrue(is_valid_callsign("ON3VZ/P"))

    def test_valid_us_call(self):
        self.assertTrue(is_valid_callsign("W1AW"))

    def test_empty(self):
        self.assertFalse(is_valid_callsign(""))

    def test_whitespace(self):
        self.assertFalse(is_valid_callsign("   "))

    def test_too_short(self):
        self.assertFalse(is_valid_callsign("A1"))

    def test_no_digit(self):
        self.assertFalse(is_valid_callsign("ONABC"))

    def test_no_letter(self):
        self.assertFalse(is_valid_callsign("12345"))

    def test_invalid_char(self):
        self.assertFalse(is_valid_callsign("ON3VZ!"))

    def test_lowercase_valid(self):
        # Validation is case-insensitive
        self.assertTrue(is_valid_callsign("on3vz"))


if __name__ == "__main__":
    unittest.main()
