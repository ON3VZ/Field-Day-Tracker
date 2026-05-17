"""
tests/test_end_to_end.py
=========================
End-to-end QA for N1MM Field Day Tracker.

Simulates the complete field day workflow without any GUI:
  1.  Create field day
  2.  Import station CSV
  3.  Receive N1MM UDP contacts (simulated)
  4.  Verify matrix updates
  5.  Apply manual overrides
  6.  Run manual sync / recalculate
  7.  Re-import CSV (re-import rules)
  8.  Export CSV
  9.  Export PDF
  10. Export HTML
  11. Restart (reload from disk) → verify state preserved
  12. Verify all 7 business rules strictly enforced
  13. Test strict / non-strict callsign matching
  14. Test frequency → band derivation
  15. Test period boundary conditions
  16. Test token encryption round-trip
  17. Verify settings persist across restarts

Run with:
    python -m unittest tests.test_end_to_end -v
"""

import csv
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.app_controller import AppController
from app.core.models import AppSettings, FieldDay, ReceivedQSO, Station
from app.core.status import Status
from app.integrations.n1mm_parser import N1MMParser


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _utc(offset_hours: float = 0) -> str:
    base = datetime(2025, 6, 21, 8, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(hours=offset_hours)).isoformat()


def _make_fieldday(name="FD2025", bands=None) -> FieldDay:
    fd = FieldDay()
    fd.name = name
    fd.location = "Ghent, Belgium"
    fd.event_callsign = "ON0TEST"
    fd.organizer = "WLD"
    fd.start_utc = _utc(-1)   # 1 hour before base
    fd.end_utc   = _utc(23)   # 23 hours after base
    fd.selected_bands = bands or ["160m", "80m", "40m", "20m"]
    return fd


def _n1mm_xml(call: str, band: str, mode: str = "CW",
              freq_10hz: int = 703000,
              ts: str = "2025-06-21 10:00:00") -> str:
    return f"""<contactinfo>
    <app>N1MM</app>
    <contestname>FDREG1</contestname>
    <timestamp>{ts}</timestamp>
    <call>{call}</call>
    <band>{band.upper()}</band>
    <rxfreq>{freq_10hz}</rxfreq>
    <txfreq>{freq_10hz}</txfreq>
    <mode>{mode}</mode>
    <ID>{call}-{band}-{ts.replace(' ','-')}</ID>
    <mycall>ON0TEST</mycall>
</contactinfo>"""


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["callsign","name","club","remarks"])
        writer.writeheader()
        writer.writerows(rows)


class BaseE2ETest(unittest.TestCase):
    """Base class: creates a temp app_root and controller."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ctrl = AppController(self.tmp)
        self.ctrl._settings = AppSettings()

    def tearDown(self):
        if self.ctrl._listener:
            self.ctrl._listener.stop()
        shutil.rmtree(self.tmp)

    def _fresh_ctrl(self) -> AppController:
        """Simulate app restart: new controller on same app_root."""
        if self.ctrl._listener:
            self.ctrl._listener.stop()
        ctrl = AppController(self.tmp)
        ctrl._settings = AppSettings.from_dict(
            self.ctrl._settings_repo.load().to_dict()
        )
        return ctrl

    def _inject_qso(self, xml: str) -> ReceivedQSO | None:
        """Parse and inject a simulated N1MM QSO into the controller."""
        qso = N1MMParser.parse(xml)
        if qso is None:
            return None
        self.ctrl._qsos = self.ctrl._fd_repo.append_qso(qso, self.ctrl._qsos)
        self.ctrl._fd_repo.save_qsos(self.ctrl._qsos)
        ctx = self.ctrl._build_context()
        self.ctrl._matrix, _ = __import__(
            "app.core.sync_engine", fromlist=["SyncEngine"]
        ).SyncEngine.process_single_qso(qso, ctx, self.ctrl._matrix)
        return qso


# ===========================================================================
# 1. Field day lifecycle
# ===========================================================================

class TestFieldDayLifecycle(BaseE2ETest):

    def test_create_and_persist(self):
        fd = _make_fieldday("E2E_Persist")
        self.ctrl.create_fieldday(fd)
        self.assertTrue(self.ctrl.has_active_fieldday)
        self.assertEqual(self.ctrl.fieldday.name, "E2E_Persist")
        self.assertEqual(self.ctrl.settings.last_active_fieldday, "E2E_Persist")

    def test_last_active_restored_on_restart(self):
        self.ctrl.create_fieldday(_make_fieldday("E2E_Restart"))
        ctrl2 = self._fresh_ctrl()
        ctrl2.startup()  # should open E2E_Restart automatically
        # startup opens last_active_fieldday
        self.assertIsNotNone(ctrl2.fieldday)
        self.assertEqual(ctrl2.fieldday.name, "E2E_Restart")
        if ctrl2._listener:
            ctrl2._listener.stop()

    def test_multiple_fielddays_listed(self):
        self.ctrl.create_fieldday(_make_fieldday("FD_A"))
        self.ctrl.create_fieldday(_make_fieldday("FD_B"))
        names = self.ctrl.list_fielddays()
        self.assertIn("FD_A", names)
        self.assertIn("FD_B", names)

    def test_switch_fieldday(self):
        self.ctrl.create_fieldday(_make_fieldday("FD_X"))
        self.ctrl.create_fieldday(_make_fieldday("FD_Y"))
        self.ctrl.open_fieldday("FD_X")
        self.assertEqual(self.ctrl.fieldday.name, "FD_X")

    def test_edit_fieldday_recalculates(self):
        self.ctrl.create_fieldday(_make_fieldday("E2E_Edit"))
        fd = self.ctrl.fieldday
        fd.selected_bands = ["40m"]
        calls = []
        self.ctrl.register_on_matrix_changed(lambda: calls.append(1))
        self.ctrl.update_fieldday(fd)
        self.assertGreater(len(calls), 0)

    def test_invalid_period_detected(self):
        fd = _make_fieldday("BadPeriod")
        fd.start_utc = _utc(10)
        fd.end_utc   = _utc(0)   # end before start
        # is_valid_period should return False
        self.assertFalse(fd.is_valid_period())


# ===========================================================================
# 2. CSV import workflow
# ===========================================================================

class TestCSVImportWorkflow(BaseE2ETest):

    def setUp(self):
        super().setUp()
        self.ctrl.create_fieldday(_make_fieldday())
        self.csv_path = self.tmp / "stations.csv"

    def test_fresh_import(self):
        _write_csv(self.csv_path, [
            {"callsign": "ON3VZ", "name": "Cornelis", "club": "WLD", "remarks": ""},
            {"callsign": "ON4ABC", "name": "Jan",      "club": "UBA", "remarks": ""},
            {"callsign": "ON5XY",  "name": "",         "club": "",    "remarks": ""},
        ])
        result = self.ctrl.import_csv(self.csv_path)
        self.assertTrue(result.success)
        self.assertEqual(len(self.ctrl.stations), 3)
        self.assertEqual(len(result.added), 3)

    def test_reimport_updates_name(self):
        _write_csv(self.csv_path, [{"callsign":"ON3VZ","name":"Old","club":"","remarks":""}])
        self.ctrl.import_csv(self.csv_path)
        _write_csv(self.csv_path, [{"callsign":"ON3VZ","name":"New","club":"","remarks":""}])
        self.ctrl.import_csv(self.csv_path)
        s = next(s for s in self.ctrl.stations if s.normalized_callsign == "ON3VZ")
        self.assertEqual(s.name, "New")

    def test_reimport_flags_missing_station(self):
        _write_csv(self.csv_path, [
            {"callsign":"ON3VZ","name":"","club":"","remarks":""},
            {"callsign":"ON4ABC","name":"","club":"","remarks":""},
        ])
        self.ctrl.import_csv(self.csv_path)
        # Re-import without ON4ABC
        _write_csv(self.csv_path, [{"callsign":"ON3VZ","name":"","club":"","remarks":""}])
        result = self.ctrl.import_csv(self.csv_path)
        self.assertIn("ON4ABC", result.removed_callsigns)

    def test_manual_station_survives_reimport(self):
        _write_csv(self.csv_path, [{"callsign":"ON3VZ","name":"","club":"","remarks":""}])
        self.ctrl.import_csv(self.csv_path)
        # Add manual station
        s = Station(callsign="ON9MANUAL", normalized_callsign="ON9MANUAL", source="manual")
        self.ctrl.add_station_manual(s)
        # Re-import (ON9MANUAL not in CSV)
        result = self.ctrl.import_csv(self.csv_path)
        self.assertIn("ON9MANUAL", result.manually_added_kept)
        norms = [s.normalized_callsign for s in self.ctrl.stations]
        self.assertIn("ON9MANUAL", norms)

    def test_invalid_callsign_skipped(self):
        _write_csv(self.csv_path, [
            {"callsign":"ON3VZ","name":"","club":"","remarks":""},
            {"callsign":"INVALID!!","name":"","club":"","remarks":""},
            {"callsign":"NODIGITS","name":"","club":"","remarks":""},
        ])
        result = self.ctrl.import_csv(self.csv_path)
        self.assertEqual(len(self.ctrl.stations), 1)
        self.assertEqual(len(result.skipped_invalid), 2)

    def test_custom_column_mapping(self):
        path = self.tmp / "dutch.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            f.write("Roepnaam,Naam,Club,Opmerkingen\n")
            f.write("ON3VZ,Cornelis,WLD,secretaris\n")
        s = AppSettings()
        s.csv_column_mapping = {
            "callsign": "Roepnaam", "name": "Naam",
            "club": "Club", "remarks": "Opmerkingen",
        }
        self.ctrl._settings = s
        result = self.ctrl.import_csv(path)
        self.assertTrue(result.success)
        st = self.ctrl.stations[0]
        self.assertEqual(st.normalized_callsign, "ON3VZ")
        self.assertEqual(st.name, "Cornelis")
        self.assertEqual(st.remarks, "secretaris")


# ===========================================================================
# 3. N1MM QSO reception and matrix update
# ===========================================================================

class TestQSOReceptionAndMatrix(BaseE2ETest):

    def setUp(self):
        super().setUp()
        self.ctrl.create_fieldday(_make_fieldday())
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [
            {"callsign":"ON3VZ","name":"Cornelis","club":"WLD","remarks":""},
            {"callsign":"ON4ABC","name":"Jan","club":"UBA","remarks":""},
            {"callsign":"ON5XY","name":"","club":"","remarks":""},
        ])
        self.ctrl.import_csv(csv_path)

    def test_qso_marks_cell_worked(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )

    def test_other_bands_unaffected(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "80m")].status,
            Status.NOT_WORKED,
        )

    def test_unknown_callsign_ignored(self):
        xml = _n1mm_xml("ON9ZZZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        # ON9ZZZ should NOT appear in matrix
        self.assertNotIn(("ON9ZZZ", "40m"), self.ctrl.matrix)

    def test_qso_outside_period_ignored(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-20 10:00:00")  # day before
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.NOT_WORKED,
        )

    def test_multiple_qsos_same_band_still_worked_once(self):
        for i in range(5):
            xml = _n1mm_xml("ON3VZ", "40M", ts=f"2025-06-21 {10+i:02d}:00:00")
            self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )
        # Only 1 worked combination for this station+band
        worked = sum(1 for (nc, b), c in self.ctrl.matrix.items()
                     if nc == "ON3VZ" and c.status.is_worked())
        self.assertEqual(worked, 1)

    def test_band_derived_from_frequency(self):
        # No band field — only frequency
        xml = """<contactinfo>
            <app>N1MM</app><contestname>FDREG1</contestname>
            <timestamp>2025-06-21 10:00:00</timestamp>
            <call>ON3VZ</call>
            <band></band>
            <rxfreq>703000</rxfreq>
            <mode>CW</mode>
            <ID>freq-test-1</ID>
            <mycall>ON0TEST</mycall>
        </contactinfo>"""
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )

    def test_mode_and_freq_stored(self):
        xml = _n1mm_xml("ON3VZ", "40M", mode="SSB",
                        freq_10hz=703500, ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        cell = self.ctrl.matrix[("ON3VZ", "40m")]
        self.assertEqual(cell.mode, "SSB")
        self.assertIsNotNone(cell.frequency_hz)

    def test_timestamp_stored_in_matrix(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 12:30:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        cell = self.ctrl.matrix[("ON3VZ", "40m")]
        self.assertIsNotNone(cell.worked_timestamp_utc)
        self.assertIn("12:30", cell.worked_timestamp_utc)

    def test_malformed_xml_does_not_crash(self):
        bad_messages = [
            "",
            "not xml at all",
            "<score><total>100</total></score>",
            "<contactinfo></contactinfo>",
            b"\xff\xfe broken bytes",
        ]
        for msg in bad_messages:
            try:
                qso = N1MMParser.parse(msg)
                if qso:
                    self.ctrl._on_qso_received(qso)
            except Exception as e:
                self.fail(f"Parser crashed on {msg!r}: {e}")


# ===========================================================================
# 4. Manual overrides (Business Rule 1: override always wins)
# ===========================================================================

class TestManualOverrides(BaseE2ETest):

    def setUp(self):
        super().setUp()
        self.ctrl.create_fieldday(_make_fieldday())
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [
            {"callsign":"ON3VZ","name":"","club":"","remarks":""},
            {"callsign":"ON4ABC","name":"","club":"","remarks":""},
        ])
        self.ctrl.import_csv(csv_path)

    def test_manual_worked_wins_over_not_worked(self):
        """No QSO, but manual_worked → cell shows worked."""
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_WORKED)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.MANUAL_WORKED,
        )
        self.assertTrue(self.ctrl.matrix[("ON3VZ", "40m")].has_override)

    def test_manual_not_worked_wins_over_n1mm(self):
        """N1MM logged QSO but manual_not_worked → cell shows not worked."""
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_NOT_WORKED)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.MANUAL_NOT_WORKED,
        )

    def test_excluded_wins_over_n1mm(self):
        xml = _n1mm_xml("ON3VZ", "80M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.ctrl.set_override("ON3VZ", "80m", Status.EXCLUDED)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "80m")].status,
            Status.EXCLUDED,
        )

    def test_clear_override_restores_n1mm(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_NOT_WORKED)
        self.ctrl.clear_override("ON3VZ", "40m")
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )
        self.assertFalse(self.ctrl.matrix[("ON3VZ", "40m")].has_override)

    def test_override_per_band_independent(self):
        """Override on 40m does not affect 80m or 160m."""
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_WORKED)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "80m")].status,
            Status.NOT_WORKED,
        )
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "160m")].status,
            Status.NOT_WORKED,
        )

    def test_overrides_survive_recalculate(self):
        """Manual sync must not lose overrides."""
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_WORKED)
        self.ctrl.recalculate()
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.MANUAL_WORKED,
        )

    def test_overrides_persist_across_restart(self):
        self.ctrl.set_override("ON3VZ", "40m", Status.MANUAL_WORKED)
        ctrl2 = self._fresh_ctrl()
        ctrl2.open_fieldday("FD2025")
        self.assertEqual(
            ctrl2.matrix[("ON3VZ", "40m")].status,
            Status.MANUAL_WORKED,
        )

    def test_example_from_spec(self):
        """ON3VZ: 160m=manual worked, 80m=auto unworked, 40m=auto worked."""
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.ctrl.set_override("ON3VZ", "160m", Status.MANUAL_WORKED)

        self.assertEqual(self.ctrl.matrix[("ON3VZ", "160m")].status, Status.MANUAL_WORKED)
        self.assertEqual(self.ctrl.matrix[("ON3VZ", "80m")].status,  Status.NOT_WORKED)
        self.assertEqual(self.ctrl.matrix[("ON3VZ", "40m")].status,  Status.WORKED_BY_N1MM)


# ===========================================================================
# 5. Callsign matching modes (Business Rules 6 & 7)
# ===========================================================================

class TestCallsignMatchingModes(BaseE2ETest):

    def setUp(self):
        super().setUp()
        self.ctrl.create_fieldday(_make_fieldday())
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [{"callsign":"ON3VZ","name":"","club":"","remarks":""}])
        self.ctrl.import_csv(csv_path)

    def test_nonstrict_portable_matches(self):
        """ON3VZ/P matches ON3VZ when strict=False (default)."""
        self.ctrl._settings.strict_callsign_matching = False
        xml = _n1mm_xml("ON3VZ/P", "40M", ts="2025-06-21 10:00:00")
        qso = N1MMParser.parse(xml, strict=False)
        self.assertEqual(qso.normalized_callsign, "ON3VZ")
        self.ctrl._on_qso_received(qso)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )

    def test_nonstrict_qrp_matches(self):
        """ON3VZ/QRP matches ON3VZ when strict=False."""
        self.ctrl._settings.strict_callsign_matching = False
        xml = _n1mm_xml("ON3VZ/QRP", "80M", ts="2025-06-21 10:00:00")
        qso = N1MMParser.parse(xml, strict=False)
        self.ctrl._on_qso_received(qso)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "80m")].status,
            Status.WORKED_BY_N1MM,
        )

    def test_strict_portable_does_not_match(self):
        """ON3VZ/P does NOT match ON3VZ when strict=True."""
        self.ctrl._settings.strict_callsign_matching = True
        xml = _n1mm_xml("ON3VZ/P", "40M", ts="2025-06-21 10:00:00")
        qso = N1MMParser.parse(xml, strict=True)
        self.assertEqual(qso.normalized_callsign, "ON3VZ/P")
        self.ctrl._on_qso_received(qso)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.NOT_WORKED,
        )

    def test_original_callsign_always_preserved(self):
        xml = _n1mm_xml("ON3VZ/P", "40M", ts="2025-06-21 10:00:00")
        qso = N1MMParser.parse(xml, strict=False)
        self.assertEqual(qso.original_callsign, "ON3VZ/P")
        self.assertEqual(qso.normalized_callsign, "ON3VZ")


# ===========================================================================
# 6. Period filtering (Business Rule 2)
# ===========================================================================

class TestPeriodFiltering(BaseE2ETest):

    def setUp(self):
        super().setUp()
        fd = _make_fieldday()
        fd.start_utc = _utc(0)   # exactly base
        fd.end_utc   = _utc(24)  # 24h later
        self.ctrl.create_fieldday(fd)
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [{"callsign":"ON3VZ","name":"","club":"","remarks":""}])
        self.ctrl.import_csv(csv_path)

    def test_qso_at_start_boundary_counts(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 08:00:00")  # exact start
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )

    def test_qso_at_end_boundary_counts(self):
        xml = _n1mm_xml("ON3VZ", "80M", ts="2025-06-22 08:00:00")  # exact end
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "80m")].status,
            Status.WORKED_BY_N1MM,
        )

    def test_qso_one_second_before_start_ignored(self):
        xml = _n1mm_xml("ON3VZ", "160M", ts="2025-06-21 07:59:59")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "160m")].status,
            Status.NOT_WORKED,
        )

    def test_qso_after_end_ignored(self):
        xml = _n1mm_xml("ON3VZ", "20M", ts="2025-06-22 09:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "20m")].status,
            Status.NOT_WORKED,
        )

    def test_manual_sync_ignores_out_of_period(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-23 10:00:00")
        qso = N1MMParser.parse(xml)
        self.ctrl._qsos.append(qso)
        result = self.ctrl.recalculate()
        self.assertEqual(result.qsos_ignored_out_of_period, 1)
        self.assertEqual(
            self.ctrl.matrix[("ON3VZ", "40m")].status,
            Status.NOT_WORKED,
        )


# ===========================================================================
# 7. Manual sync / recalculate
# ===========================================================================

class TestManualSync(BaseE2ETest):

    def setUp(self):
        super().setUp()
        self.ctrl.create_fieldday(_make_fieldday())
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [
            {"callsign":"ON3VZ","name":"","club":"","remarks":""},
            {"callsign":"ON4ABC","name":"","club":"","remarks":""},
        ])
        self.ctrl.import_csv(csv_path)

    def test_recalculate_produces_correct_counts(self):
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        result = self.ctrl.recalculate()
        # 2 stations × 4 bands = 8 combinations; 1 worked
        self.assertEqual(result.worked_combinations, 1)
        self.assertEqual(result.unworked_combinations, 7)

    def test_recalculate_from_scratch_matches_incremental(self):
        """Full recalculate produces same result as incremental updates."""
        qsos_xml = [
            _n1mm_xml("ON3VZ",  "40M", ts="2025-06-21 10:00:00"),
            _n1mm_xml("ON3VZ",  "80M", ts="2025-06-21 11:00:00"),
            _n1mm_xml("ON4ABC", "40M", ts="2025-06-21 12:00:00"),
        ]
        for xml in qsos_xml:
            self.ctrl._on_qso_received(N1MMParser.parse(xml))

        # Save incremental state
        inc_matrix = {k: v.status for k, v in self.ctrl.matrix.items()}

        # Full recalculate
        self.ctrl.recalculate()
        rec_matrix = {k: v.status for k, v in self.ctrl.matrix.items()}

        self.assertEqual(inc_matrix, rec_matrix)

    def test_unknown_calls_reported_in_result(self):
        xml = _n1mm_xml("ON9ZZZ", "40M", ts="2025-06-21 10:00:00")
        qso = N1MMParser.parse(xml)
        self.ctrl._qsos.append(qso)
        result = self.ctrl.recalculate()
        self.assertEqual(result.qsos_ignored_unknown, 1)

    def test_statistics_summary(self):
        xml1 = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        xml2 = _n1mm_xml("ON3VZ", "80M", ts="2025-06-21 11:00:00")
        xml3 = _n1mm_xml("ON3VZ", "160M", ts="2025-06-21 12:00:00")
        xml4 = _n1mm_xml("ON3VZ", "20M",  ts="2025-06-21 13:00:00")
        for xml in [xml1, xml2, xml3, xml4]:
            self.ctrl._on_qso_received(N1MMParser.parse(xml))

        stats = self.ctrl.get_station_statistics()
        self.assertEqual(stats["fully_worked"], 1)   # ON3VZ: all 4 bands
        self.assertEqual(stats["not_worked"],   1)   # ON4ABC: none
        self.assertEqual(stats["partially_worked"], 0)

    def test_sync_timestamp_updated(self):
        before = self.ctrl.fieldday.last_sync_utc
        self.ctrl.recalculate()
        after = self.ctrl.fieldday.last_sync_utc
        self.assertIsNotNone(after)
        if before:
            self.assertGreaterEqual(after, before)


# ===========================================================================
# 8. Data persistence (restart simulation)
# ===========================================================================

class TestDataPersistence(BaseE2ETest):

    def test_qsos_survive_restart(self):
        self.ctrl.create_fieldday(_make_fieldday())
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [{"callsign":"ON3VZ","name":"","club":"","remarks":""}])
        self.ctrl.import_csv(csv_path)
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))

        ctrl2 = self._fresh_ctrl()
        ctrl2.open_fieldday("FD2025")
        self.assertEqual(len(ctrl2._qsos), 1)
        self.assertEqual(
            ctrl2.matrix[("ON3VZ", "40m")].status,
            Status.WORKED_BY_N1MM,
        )

    def test_stations_survive_restart(self):
        self.ctrl.create_fieldday(_make_fieldday())
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [
            {"callsign":"ON3VZ","name":"Cornelis","club":"WLD","remarks":""},
            {"callsign":"ON4ABC","name":"","club":"","remarks":""},
        ])
        self.ctrl.import_csv(csv_path)

        ctrl2 = self._fresh_ctrl()
        ctrl2.open_fieldday("FD2025")
        self.assertEqual(len(ctrl2.stations), 2)
        norms = [s.normalized_callsign for s in ctrl2.stations]
        self.assertIn("ON3VZ", norms)
        self.assertIn("ON4ABC", norms)

    def test_settings_survive_restart(self):
        s = self.ctrl._settings
        s.ui_language = "nl"
        s.strict_callsign_matching = True
        s.n1mm_udp_port = 12099
        self.ctrl._settings_repo.save(s)

        ctrl2 = self._fresh_ctrl()
        loaded = ctrl2._settings_repo.load()
        self.assertEqual(loaded.ui_language, "nl")
        self.assertTrue(loaded.strict_callsign_matching)
        self.assertEqual(loaded.n1mm_udp_port, 12099)

    def test_fieldday_metadata_survives_restart(self):
        self.ctrl.create_fieldday(_make_fieldday())
        ctrl2 = self._fresh_ctrl()
        ctrl2.open_fieldday("FD2025")
        fd = ctrl2.fieldday
        self.assertEqual(fd.location, "Ghent, Belgium")
        self.assertEqual(fd.event_callsign, "ON0TEST")
        self.assertEqual(fd.organizer, "WLD")
        self.assertTrue(fd.is_valid_period())


# ===========================================================================
# 9. Export functions
# ===========================================================================

class TestExports(BaseE2ETest):

    def setUp(self):
        super().setUp()
        self.ctrl.create_fieldday(_make_fieldday())
        csv_path = self.tmp / "st.csv"
        _write_csv(csv_path, [
            {"callsign":"ON3VZ","name":"Cornelis","club":"WLD","remarks":"test"},
            {"callsign":"ON4ABC","name":"Jan","club":"UBA","remarks":""},
        ])
        self.ctrl.import_csv(csv_path)
        xml = _n1mm_xml("ON3VZ", "40M", ts="2025-06-21 10:00:00")
        self.ctrl._on_qso_received(N1MMParser.parse(xml))
        self.ctrl.set_override("ON4ABC", "80m", Status.MANUAL_WORKED)

    def test_csv_export(self):
        path = self.tmp / "exports" / "test.csv"
        result = self.ctrl.export_csv(path)
        self.assertTrue(result.success)
        self.assertTrue(path.exists())
        # 2 stations × 4 bands = 8 rows
        self.assertEqual(result.rows_written, 8)
        with path.open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        worked = [r for r in rows if r["status"] == "worked_by_n1mm"]
        self.assertEqual(len(worked), 1)
        self.assertEqual(worked[0]["normalized_callsign"], "ON3VZ")
        overridden = [r for r in rows if r["manual_override"] == "yes"]
        self.assertEqual(len(overridden), 1)

    def test_pdf_export(self):
        path = self.tmp / "exports" / "test.pdf"
        result = self.ctrl.export_pdf(path)
        self.assertTrue(result.success, result.error)
        self.assertTrue(path.exists())
        self.assertTrue(path.stat().st_size > 2000)  # valid PDF, size varies
        header = path.read_bytes()[:5]
        self.assertEqual(header, b"%PDF-")

    def test_html_export(self):
        from app.exporters.html_exporter import HTMLExporter
        path = self.tmp / "exports" / "index.html"
        result = HTMLExporter.export(
            path, self.ctrl.fieldday,
            self.ctrl.stations, self.ctrl.matrix,
        )
        self.assertTrue(result.success)
        html = path.read_text(encoding="utf-8")
        self.assertIn("ON3VZ", html)
        self.assertIn("FD2025", html)
        self.assertIn("meta http-equiv", html.lower())

    def test_export_folder_created_automatically(self):
        path = self.tmp / "deep" / "nested" / "export.csv"
        result = self.ctrl.export_csv(path)
        self.assertTrue(result.success)
        self.assertTrue(path.exists())


# ===========================================================================
# 10. Token security
# ===========================================================================

class TestTokenSecurity(unittest.TestCase):

    def test_encrypt_decrypt_roundtrip(self):
        from app.security.token_store import TokenStore
        plain = "ghp_TestToken123_FieldDay"
        enc = TokenStore.encrypt(plain)
        self.assertTrue(enc.startswith("enc:"))
        self.assertEqual(TokenStore.decrypt(enc), plain)

    def test_corrupt_ciphertext_returns_empty(self):
        from app.security.token_store import TokenStore
        self.assertEqual(TokenStore.decrypt("enc:notvalidbase64!!!"), "")

    def test_empty_token_stays_empty(self):
        from app.security.token_store import TokenStore
        self.assertEqual(TokenStore.encrypt(""), "")
        self.assertEqual(TokenStore.decrypt(""), "")

    def test_token_not_visible_in_settings_file(self):
        """Encrypted token in JSON must not contain the plain token."""
        from app.security.token_store import TokenStore
        import json, tempfile
        plain = "ghp_SuperSecretToken99"
        enc   = TokenStore.encrypt(plain)
        data  = {"github_token_encrypted": enc}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            fname = f.name
        raw = Path(fname).read_text()
        self.assertNotIn(plain, raw)
        Path(fname).unlink()


# ===========================================================================
# 11. N1MM XML parser edge cases
# ===========================================================================

class TestN1MMParserEdgeCases(unittest.TestCase):

    def test_fdreg1_contest(self):
        xml = _n1mm_xml("ON3VZ", "40M")
        qso = N1MMParser.parse(xml)
        self.assertEqual(qso.contest_name, "FDREG1")

    def test_all_bands_parsed(self):
        band_tests = [
            ("160M", "160m", 180000),
            ("80M",  "80m",  358000),
            ("40M",  "40m",  703000),
            ("20M",  "20m",  1420000),
            ("2M",   "2m",   14550000),
            ("70CM", "70cm", 43200000),
        ]
        for n1mm_band, expected_band, freq in band_tests:
            xml = _n1mm_xml("ON3VZ", n1mm_band, freq_10hz=freq)
            qso = N1MMParser.parse(xml)
            self.assertIsNotNone(qso, f"Failed for {n1mm_band}")
            self.assertEqual(qso.band, expected_band,
                             f"Band mismatch for {n1mm_band}")

    def test_original_callsign_preserved(self):
        xml = _n1mm_xml("ON3VZ/P", "40M")
        qso = N1MMParser.parse(xml, strict=False)
        self.assertEqual(qso.original_callsign, "ON3VZ/P")
        self.assertEqual(qso.normalized_callsign, "ON3VZ")

    def test_n1mm_id_stored(self):
        xml = _n1mm_xml("ON3VZ", "40M")
        qso = N1MMParser.parse(xml)
        self.assertTrue(bool(qso.n1mm_id))

    def test_raw_message_stored(self):
        xml = _n1mm_xml("ON3VZ", "40M")
        qso = N1MMParser.parse(xml)
        self.assertIn("ON3VZ", qso.raw_message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
