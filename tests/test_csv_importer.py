"""
tests/test_csv_importer.py
==========================
Unit tests for app.importers.csv_importer

Run with:
    python -m unittest tests.test_csv_importer -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.importers.csv_importer import CSVImporter, ImportResult
from app.core.models import Station


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(content: str, suffix=".csv") -> Path:
    """Write content to a temp CSV file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return Path(f.name)


def _station(callsign: str, source: str = "csv", remarks: str = "") -> Station:
    s = Station()
    s.callsign = callsign
    s.normalized_callsign = callsign.upper()
    s.source = source
    s.remarks = remarks
    return s


# ---------------------------------------------------------------------------
# Fresh import (no existing stations)
# ---------------------------------------------------------------------------

class TestFreshImport(unittest.TestCase):

    def test_basic_import(self):
        path = _write_csv(
            "callsign,name,club,remarks\n"
            "ON3VZ,Cornelis,WLD,\n"
            "ON4ABC,,,\n"
        )
        result = CSVImporter.import_csv(path)
        self.assertTrue(result.success)
        self.assertEqual(len(result.stations), 2)
        self.assertIn("ON3VZ", result.added)
        self.assertIn("ON4ABC", result.added)
        self.assertEqual(result.total_csv_rows, 2)

    def test_optional_fields_populated(self):
        path = _write_csv(
            "callsign,name,club,remarks\n"
            "ON3VZ,Cornelis,WLD,Club secretary\n"
        )
        result = CSVImporter.import_csv(path)
        s = result.stations[0]
        self.assertEqual(s.name, "Cornelis")
        self.assertEqual(s.club, "WLD")
        self.assertEqual(s.remarks, "Club secretary")
        self.assertEqual(s.source, "csv")

    def test_optional_fields_missing_columns(self):
        """CSV with only callsign column — no error."""
        path = _write_csv("callsign\nON3VZ\nON4ABC\n")
        result = CSVImporter.import_csv(path)
        self.assertEqual(len(result.stations), 2)
        self.assertEqual(result.stations[0].name, "")

    def test_invalid_callsign_skipped(self):
        path = _write_csv(
            "callsign\n"
            "ON3VZ\n"
            "INVALID!!\n"
            "NODIGITS\n"
            "ON4ABC\n"
        )
        result = CSVImporter.import_csv(path)
        self.assertEqual(len(result.stations), 2)
        self.assertIn("INVALID!!", result.skipped_invalid)
        self.assertIn("NODIGITS", result.skipped_invalid)

    def test_duplicate_callsign_in_csv(self):
        path = _write_csv(
            "callsign\n"
            "ON3VZ\n"
            "ON3VZ\n"   # duplicate
            "ON4ABC\n"
        )
        result = CSVImporter.import_csv(path)
        self.assertEqual(len(result.stations), 2)
        self.assertEqual(len(result.skipped_duplicate), 1)

    def test_case_insensitive_callsign(self):
        path = _write_csv("callsign\non3vz\nON4ABC\n")
        result = CSVImporter.import_csv(path)
        norms = [s.normalized_callsign for s in result.stations]
        self.assertIn("ON3VZ", norms)
        self.assertIn("ON4ABC", norms)

    def test_missing_callsign_column_error(self):
        path = _write_csv("name,club\nCornélis,WLD\n")
        result = CSVImporter.import_csv(path)
        self.assertFalse(result.success)
        self.assertTrue(any("callsign" in e for e in result.errors))

    def test_empty_file_error(self):
        path = _write_csv("")
        result = CSVImporter.import_csv(path)
        self.assertFalse(result.success)

    def test_nonexistent_file(self):
        result = CSVImporter.import_csv(Path("/nonexistent/path/file.csv"))
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)

    def test_normalised_callsign_stored(self):
        path = _write_csv("callsign\non3vz/p\n")
        result = CSVImporter.import_csv(path)
        s = result.stations[0]
        self.assertEqual(s.callsign, "on3vz/p")        # original preserved
        self.assertEqual(s.normalized_callsign, "ON3VZ")  # normalised (non-strict)

    def test_strict_matching_keeps_suffix(self):
        path = _write_csv("callsign\nON3VZ/P\n")
        result = CSVImporter.import_csv(path, strict=True)
        s = result.stations[0]
        self.assertEqual(s.normalized_callsign, "ON3VZ/P")

    def test_bom_utf8_handled(self):
        """UTF-8 BOM (from Excel) should not break parsing."""
        path = _write_csv("\ufeffcallsign,name\nON3VZ,Cornelis\n")
        result = CSVImporter.import_csv(path)
        self.assertEqual(len(result.stations), 1)

    def test_semicolon_delimiter(self):
        path = _write_csv("callsign;name;club\nON3VZ;Cornelis;WLD\nON4ABC;;\n")
        result = CSVImporter.import_csv(path)
        self.assertEqual(len(result.stations), 2)

    def test_whitespace_trimmed(self):
        path = _write_csv("callsign,name\n  ON3VZ  ,  Cornelis  \n")
        result = CSVImporter.import_csv(path)
        self.assertEqual(result.stations[0].normalized_callsign, "ON3VZ")
        self.assertEqual(result.stations[0].name, "Cornelis")


# ---------------------------------------------------------------------------
# Re-import (existing stations present)
# ---------------------------------------------------------------------------

class TestReImport(unittest.TestCase):

    def test_existing_station_updated(self):
        """Station in new CSV → data refreshed."""
        existing = [_station("ON3VZ")]
        path = _write_csv("callsign,name\nON3VZ,NewName\n")
        result = CSVImporter.import_csv(path, existing)
        self.assertIn("ON3VZ", result.updated)
        s = next(s for s in result.stations if s.normalized_callsign == "ON3VZ")
        self.assertEqual(s.name, "NewName")

    def test_new_station_added_on_reimport(self):
        existing = [_station("ON3VZ")]
        path = _write_csv("callsign\nON3VZ\nON4ABC\n")
        result = CSVImporter.import_csv(path, existing)
        self.assertIn("ON4ABC", result.added)
        self.assertEqual(len(result.stations), 2)

    def test_missing_csv_station_flagged_not_removed(self):
        """Station absent from new CSV → in removed_callsigns, NOT deleted."""
        existing = [_station("ON3VZ"), _station("ON4ABC")]
        path = _write_csv("callsign\nON3VZ\n")  # ON4ABC missing
        result = CSVImporter.import_csv(path, existing)
        self.assertIn("ON4ABC", result.removed_callsigns)
        # Still present in result.stations (caller decides whether to remove)
        norms = [s.normalized_callsign for s in result.stations]
        self.assertIn("ON4ABC", norms)

    def test_manual_station_always_kept(self):
        """Manually added station not in CSV → kept unconditionally."""
        manual = _station("ON5XY", source="manual")
        existing = [_station("ON3VZ"), manual]
        path = _write_csv("callsign\nON3VZ\n")  # ON5XY not in CSV
        result = CSVImporter.import_csv(path, existing)
        self.assertIn("ON5XY", result.manually_added_kept)
        self.assertNotIn("ON5XY", result.removed_callsigns)
        norms = [s.normalized_callsign for s in result.stations]
        self.assertIn("ON5XY", norms)

    def test_remarks_preserved_if_csv_empty(self):
        """If CSV remarks column is blank, existing remarks are kept."""
        existing = [_station("ON3VZ", remarks="My note")]
        path = _write_csv("callsign,remarks\nON3VZ,\n")
        result = CSVImporter.import_csv(path, existing)
        s = next(s for s in result.stations if s.normalized_callsign == "ON3VZ")
        self.assertEqual(s.remarks, "My note")

    def test_remarks_updated_if_csv_has_value(self):
        existing = [_station("ON3VZ", remarks="Old note")]
        path = _write_csv("callsign,remarks\nON3VZ,New note\n")
        result = CSVImporter.import_csv(path, existing)
        s = next(s for s in result.stations if s.normalized_callsign == "ON3VZ")
        self.assertEqual(s.remarks, "New note")

    def test_order_existing_first_new_at_end(self):
        """Re-import preserves existing order; new stations go at the end."""
        existing = [_station("ON3VZ"), _station("ON4ABC")]
        path = _write_csv("callsign\nON4ABC\nON3VZ\nON5XY\n")
        result = CSVImporter.import_csv(path, existing)
        norms = [s.normalized_callsign for s in result.stations]
        # Existing order preserved
        self.assertEqual(norms.index("ON3VZ"), 0)
        self.assertEqual(norms.index("ON4ABC"), 1)
        # New station at end
        self.assertEqual(norms[-1], "ON5XY")

    def test_empty_existing_list(self):
        path = _write_csv("callsign\nON3VZ\n")
        result = CSVImporter.import_csv(path, [])
        self.assertEqual(len(result.stations), 1)


# ---------------------------------------------------------------------------
# apply_removals
# ---------------------------------------------------------------------------

class TestApplyRemovals(unittest.TestCase):

    def test_removes_specified_callsigns(self):
        stations = [_station("ON3VZ"), _station("ON4ABC"), _station("ON5XY")]
        result = CSVImporter.apply_removals(stations, ["ON4ABC"])
        norms = [s.normalized_callsign for s in result]
        self.assertNotIn("ON4ABC", norms)
        self.assertIn("ON3VZ", norms)
        self.assertIn("ON5XY", norms)

    def test_empty_removal_list(self):
        stations = [_station("ON3VZ")]
        result = CSVImporter.apply_removals(stations, [])
        self.assertEqual(len(result), 1)

    def test_remove_all(self):
        stations = [_station("ON3VZ"), _station("ON4ABC")]
        result = CSVImporter.apply_removals(stations, ["ON3VZ", "ON4ABC"])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
