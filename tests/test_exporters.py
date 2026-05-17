"""
tests/test_exporters.py
========================
Tests for app.exporters.csv_exporter and app.exporters.pdf_exporter

Run with:
    python -m unittest tests.test_exporters -v
"""

import csv
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.exporters.csv_exporter import CSVExporter
from app.exporters.pdf_exporter import PDFExporter
from app.core.models import (
    AppSettings, FieldDay, Station, StationBandStatus, Override
)
from app.core.status import Status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(h: float = 0) -> str:
    base = datetime(2025, 6, 21, 8, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(hours=h)).isoformat()


def _fieldday(bands=None) -> FieldDay:
    fd = FieldDay()
    fd.name = "TestFD2025"
    fd.location = "Ghent"
    fd.event_callsign = "ON0TEST"
    fd.organizer = "WLD"
    fd.start_utc = _utc(-1)
    fd.end_utc = _utc(23)
    fd.selected_bands = bands or ["40m", "80m", "160m"]
    return fd


def _station(call: str, name: str = "", club: str = "",
             remarks: str = "") -> Station:
    s = Station()
    s.callsign = call
    s.normalized_callsign = call.upper()
    s.name = name
    s.club = club
    s.remarks = remarks
    s.source = "csv"
    return s


def _cell(status: Status, mode: str = "CW",
          freq_hz: float | None = 7_030_000.0,
          ts: str | None = None,
          override: bool = False) -> StationBandStatus:
    c = StationBandStatus()
    c.status = status
    c.mode = mode
    c.frequency_hz = freq_hz
    c.worked_timestamp_utc = ts or _utc(5)
    c.has_override = override
    return c


def _matrix(stations, bands, worked_combos=None):
    """Build a test matrix. worked_combos = set of (norm_call, band)."""
    m = {}
    wc = worked_combos or set()
    for s in stations:
        nc = s.normalized_callsign
        for band in bands:
            if (nc, band) in wc:
                m[(nc, band)] = _cell(Status.WORKED_BY_N1MM)
            else:
                m[(nc, band)] = _cell(Status.NOT_WORKED, mode="", freq_hz=None, ts="")
    return m


# ---------------------------------------------------------------------------
# CSV Exporter
# ---------------------------------------------------------------------------

class TestCSVExporter(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fd = _fieldday()
        self.stations = [
            _station("ON3VZ", "Cornelis", "WLD", "club sec"),
            _station("ON4ABC", "Jan"),
        ]

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _export(self, worked_combos=None):
        path = self.tmp / "export.csv"
        matrix = _matrix(self.stations, self.fd.selected_bands, worked_combos or set())
        return CSVExporter.export(path, self.fd, self.stations, matrix), path

    def test_export_creates_file(self):
        result, path = self._export()
        self.assertTrue(result.success)
        self.assertTrue(path.exists())

    def test_export_row_count(self):
        """2 stations × 3 bands = 6 rows + 1 header."""
        result, path = self._export()
        self.assertEqual(result.rows_written, 6)
        with path.open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 6)

    def test_export_headers(self):
        _, path = self._export()
        with path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        expected = [
            "callsign", "normalized_callsign", "band", "status", "source",
            "mode", "frequency_mhz", "worked_timestamp_utc",
            "manual_override", "remarks",
        ]
        self.assertEqual(headers, expected)

    def test_worked_status_in_csv(self):
        result, path = self._export(
            worked_combos={("ON3VZ", "40m"), ("ON3VZ", "80m")}
        )
        with path.open(encoding="utf-8-sig") as f:
            rows = {(r["normalized_callsign"], r["band"]): r
                    for r in csv.DictReader(f)}
        self.assertEqual(rows[("ON3VZ", "40m")]["status"], "worked_by_n1mm")
        self.assertEqual(rows[("ON3VZ", "80m")]["status"], "worked_by_n1mm")
        self.assertEqual(rows[("ON3VZ", "160m")]["status"], "not_worked")
        self.assertEqual(rows[("ON4ABC", "40m")]["status"], "not_worked")

    def test_remarks_exported(self):
        _, path = self._export()
        with path.open(encoding="utf-8-sig") as f:
            rows = {r["normalized_callsign"]: r for r in csv.DictReader(f)
                    if r["band"] == "40m"}
        self.assertEqual(rows["ON3VZ"]["remarks"], "club sec")

    def test_frequency_converted_to_mhz(self):
        path = self.tmp / "freq.csv"
        matrix = {("ON3VZ", "40m"): _cell(Status.WORKED_BY_N1MM, freq_hz=7_030_000.0)}
        for s in self.stations:
            for b in self.fd.selected_bands:
                if (s.normalized_callsign, b) not in matrix:
                    matrix[(s.normalized_callsign, b)] = _cell(
                        Status.NOT_WORKED, mode="", freq_hz=None, ts="")
        CSVExporter.export(path, self.fd, self.stations, matrix)
        with path.open(encoding="utf-8-sig") as f:
            rows = {(r["normalized_callsign"], r["band"]): r
                    for r in csv.DictReader(f)}
        self.assertEqual(rows[("ON3VZ", "40m")]["frequency_mhz"], "7.0300")

    def test_manual_override_flagged(self):
        path = self.tmp / "override.csv"
        matrix = {("ON3VZ", "40m"): _cell(
            Status.MANUAL_WORKED, override=True)}
        for s in self.stations:
            for b in self.fd.selected_bands:
                if (s.normalized_callsign, b) not in matrix:
                    matrix[(s.normalized_callsign, b)] = _cell(
                        Status.NOT_WORKED, mode="", freq_hz=None, ts="")
        CSVExporter.export(path, self.fd, self.stations, matrix)
        with path.open(encoding="utf-8-sig") as f:
            rows = {(r["normalized_callsign"], r["band"]): r
                    for r in csv.DictReader(f)}
        self.assertEqual(rows[("ON3VZ", "40m")]["manual_override"], "yes")
        self.assertEqual(rows[("ON3VZ", "80m")]["manual_override"], "no")

    def test_sorted_by_callsign(self):
        _, path = self._export()
        with path.open(encoding="utf-8-sig") as f:
            calls = [r["normalized_callsign"] for r in csv.DictReader(f)]
        # Should be sorted A→Z
        self.assertEqual(calls[0], "ON3VZ")
        self.assertEqual(calls[3], "ON4ABC")

    def test_export_to_nonexistent_dir(self):
        """Parent directory is created automatically."""
        path = self.tmp / "sub" / "deep" / "export.csv"
        matrix = _matrix(self.stations, self.fd.selected_bands)
        result = CSVExporter.export(path, self.fd, self.stations, matrix)
        self.assertTrue(result.success)
        self.assertTrue(path.exists())

    def test_default_filename_format(self):
        name = CSVExporter.default_filename(self.fd)
        self.assertIn("TestFD2025", name)
        self.assertTrue(name.endswith(".csv"))

    def test_utf8_bom_for_excel(self):
        """File should start with UTF-8 BOM so Excel opens it correctly."""
        _, path = self._export()
        raw = path.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"),
                        "CSV should have UTF-8 BOM for Excel compatibility")


# ---------------------------------------------------------------------------
# PDF Exporter
# ---------------------------------------------------------------------------

class TestPDFExporter(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fd = _fieldday()
        self.stations = [
            _station("ON3VZ", "Cornelis", "WLD"),
            _station("ON4ABC", "Jan", "UBA"),
            _station("ON5XY"),
        ]
        self.matrix = _matrix(
            self.stations, self.fd.selected_bands,
            worked_combos={("ON3VZ", "40m"), ("ON3VZ", "80m"), ("ON4ABC", "40m")},
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_pdf_created(self):
        path = self.tmp / "report.pdf"
        result = PDFExporter.export(path, self.fd, self.stations, self.matrix)
        self.assertTrue(result.success, result.error)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 1000)

    def test_pdf_is_valid_pdf(self):
        path = self.tmp / "report.pdf"
        PDFExporter.export(path, self.fd, self.stations, self.matrix)
        header = path.read_bytes()[:5]
        self.assertEqual(header, b"%PDF-", "File should start with %PDF-")

    def test_pdf_with_no_stations(self):
        path = self.tmp / "empty.pdf"
        result = PDFExporter.export(
            path, self.fd, [], {}, AppSettings()
        )
        self.assertTrue(result.success, result.error)
        self.assertTrue(path.exists())

    def test_pdf_with_many_bands(self):
        """Landscape mode triggered for > 6 bands."""
        fd = _fieldday(bands=["160m","80m","40m","30m","20m","15m","10m"])
        path = self.tmp / "wide.pdf"
        matrix = _matrix(self.stations, fd.selected_bands)
        result = PDFExporter.export(path, fd, self.stations, matrix, AppSettings())
        self.assertTrue(result.success, result.error)

    def test_pdf_with_custom_colors(self):
        settings = AppSettings()
        settings.status_colors = {
            "not_worked":       "#F5F5F5",
            "worked_by_n1mm":   "#1565C0",
            "manual_worked":    "#004D40",
            "manual_not_worked":"#E65100",
            "excluded":         "#424242",
        }
        path = self.tmp / "custom_colors.pdf"
        result = PDFExporter.export(
            path, self.fd, self.stations, self.matrix, settings
        )
        self.assertTrue(result.success, result.error)

    def test_default_filename_format(self):
        name = PDFExporter.default_filename(self.fd)
        self.assertIn("TestFD2025", name)
        self.assertTrue(name.endswith(".pdf"))

    def test_pdf_with_overrides(self):
        matrix = dict(self.matrix)
        cell = _cell(Status.MANUAL_WORKED, override=True)
        matrix[("ON3VZ", "160m")] = cell
        path = self.tmp / "overrides.pdf"
        result = PDFExporter.export(
            path, self.fd, self.stations, matrix, AppSettings()
        )
        self.assertTrue(result.success, result.error)


if __name__ == "__main__":
    unittest.main()
