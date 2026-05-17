"""
tests/test_sync_engine.py
=========================
Unit tests for app.core.sync_engine

Covers all critical business rules:
  1. Manual override wins — always
  2. QSOs outside period are ignored
  3. Unknown callsigns are ignored
  4. Status is per callsign + band
  5. All timestamps compared in UTC
  6. Band derived from frequency when not set
  7. Strict / non-strict callsign matching

Run with:
    python -m unittest tests.test_sync_engine -v
"""

import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.sync_engine import SyncEngine, SyncContext
from app.core.models import FieldDay, Station, ReceivedQSO, Override, StationBandStatus
from app.core.status import Status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(offset_hours: float = 0) -> str:
    """Return a UTC ISO timestamp relative to a fixed base time."""
    base = datetime(2025, 6, 21, 10, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(hours=offset_hours)).isoformat()


def _fieldday(start_h: float = -1, end_h: float = 23) -> FieldDay:
    fd = FieldDay()
    fd.name = "TestFD"
    fd.start_utc = _utc(start_h)
    fd.end_utc = _utc(end_h)
    fd.selected_bands = ["40m", "80m", "160m"]
    return fd


def _station(norm_call: str, source: str = "csv") -> Station:
    s = Station()
    s.callsign = norm_call
    s.normalized_callsign = norm_call
    s.source = source
    return s


def _qso(
    call: str = "ON3VZ",
    band: str = "40m",
    timestamp_offset_h: float = 0,
    freq_hz: float | None = None,
    mode: str = "CW",
) -> ReceivedQSO:
    q = ReceivedQSO()
    q.original_callsign = call
    q.normalized_callsign = call.upper()
    q.band = band
    q.frequency_hz = freq_hz
    q.mode = mode
    q.timestamp_utc = _utc(timestamp_offset_h)
    q.n1mm_id = f"{call}-{band}-{timestamp_offset_h}"
    return q


def _override(norm_call: str, band: str, status: Status) -> Override:
    o = Override()
    o.normalized_callsign = norm_call
    o.band = band
    o.status = status.value
    return o


def _ctx(
    fieldday: FieldDay | None = None,
    stations: list | None = None,
    qsos: list | None = None,
    overrides: dict | None = None,
    strict: bool = False,
) -> SyncContext:
    return SyncContext(
        fieldday=fieldday or _fieldday(),
        stations=stations or [],
        qsos=qsos or [],
        overrides=overrides or {},
        strict=strict,
    )


# ---------------------------------------------------------------------------
# Basic recalculation
# ---------------------------------------------------------------------------

class TestRecalculateBasic(unittest.TestCase):

    def test_empty_context_returns_empty_matrix(self):
        matrix, result = SyncEngine.recalculate(_ctx())
        self.assertEqual(matrix, {})
        self.assertEqual(result.total_qsos_processed, 0)

    def test_station_with_no_qsos_is_not_worked(self):
        ctx = _ctx(stations=[_station("ON3VZ")])
        matrix, _ = SyncEngine.recalculate(ctx)
        for band in ["40m", "80m", "160m"]:
            self.assertEqual(
                matrix[("ON3VZ", band)].status,
                Status.NOT_WORKED,
            )

    def test_qso_marks_station_band_as_worked(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m")],
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON3VZ", "80m")].status, Status.NOT_WORKED)
        self.assertEqual(result.worked_combinations, 1)
        self.assertEqual(result.unworked_combinations, 2)

    def test_multiple_qsos_same_band_still_one_worked(self):
        """Multiple QSOs on same callsign+band → still just 'worked'."""
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[
                _qso("ON3VZ", "40m", 0),
                _qso("ON3VZ", "40m", 1),
                _qso("ON3VZ", "40m", 2),
            ],
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(result.worked_combinations, 1)

    def test_different_bands_tracked_independently(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[
                _qso("ON3VZ", "40m"),
                _qso("ON3VZ", "80m"),
            ],
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON3VZ", "80m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON3VZ", "160m")].status, Status.NOT_WORKED)
        self.assertEqual(result.worked_combinations, 2)

    def test_multiple_stations(self):
        ctx = _ctx(
            stations=[_station("ON3VZ"), _station("ON4ABC")],
            qsos=[
                _qso("ON3VZ", "40m"),
                _qso("ON4ABC", "80m"),
            ],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON4ABC", "80m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON3VZ", "80m")].status, Status.NOT_WORKED)
        self.assertEqual(matrix[("ON4ABC", "40m")].status, Status.NOT_WORKED)


# ---------------------------------------------------------------------------
# Business rule 1: Manual override always wins
# ---------------------------------------------------------------------------

class TestManualOverrideWins(unittest.TestCase):

    def test_override_manual_worked_wins_over_not_worked(self):
        """No N1MM QSO, but manual_worked override → cell is worked."""
        override = _override("ON3VZ", "40m", Status.MANUAL_WORKED)
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[],
            overrides={override.key: override},
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.MANUAL_WORKED)
        self.assertTrue(matrix[("ON3VZ", "40m")].has_override)
        self.assertEqual(result.manual_override_count, 1)

    def test_override_manual_not_worked_wins_over_n1mm(self):
        """N1MM logged a QSO, but manual_not_worked override → cell is not worked."""
        override = _override("ON3VZ", "40m", Status.MANUAL_NOT_WORKED)
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m")],
            overrides={override.key: override},
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.MANUAL_NOT_WORKED)
        self.assertTrue(matrix[("ON3VZ", "40m")].has_override)

    def test_excluded_override_wins(self):
        override = _override("ON3VZ", "40m", Status.EXCLUDED)
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m")],
            overrides={override.key: override},
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.EXCLUDED)
        self.assertEqual(result.excluded_count, 1)

    def test_override_only_affects_specified_band(self):
        """Override on 40m should not affect 80m."""
        override = _override("ON3VZ", "40m", Status.MANUAL_WORKED)
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[],
            overrides={override.key: override},
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.MANUAL_WORKED)
        self.assertEqual(matrix[("ON3VZ", "80m")].status, Status.NOT_WORKED)

    def test_different_stations_overridden_independently(self):
        o1 = _override("ON3VZ", "40m", Status.MANUAL_WORKED)
        o2 = _override("ON4ABC", "40m", Status.MANUAL_NOT_WORKED)
        ctx = _ctx(
            stations=[_station("ON3VZ"), _station("ON4ABC")],
            qsos=[_qso("ON3VZ", "40m"), _qso("ON4ABC", "40m")],
            overrides={o1.key: o1, o2.key: o2},
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.MANUAL_WORKED)
        self.assertEqual(matrix[("ON4ABC", "40m")].status, Status.MANUAL_NOT_WORKED)


# ---------------------------------------------------------------------------
# Business rule 2: QSOs outside period are ignored
# ---------------------------------------------------------------------------

class TestPeriodFiltering(unittest.TestCase):

    def test_qso_before_period_ignored(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m", timestamp_offset_h=-2)],  # before start
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.NOT_WORKED)
        self.assertEqual(result.qsos_ignored_out_of_period, 1)

    def test_qso_after_period_ignored(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m", timestamp_offset_h=25)],  # after end
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.NOT_WORKED)
        self.assertEqual(result.qsos_ignored_out_of_period, 1)

    def test_qso_at_start_boundary_counts(self):
        fd = _fieldday(start_h=0, end_h=24)
        ctx = _ctx(
            fieldday=fd,
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m", timestamp_offset_h=0)],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)

    def test_qso_at_end_boundary_counts(self):
        fd = _fieldday(start_h=0, end_h=24)
        ctx = _ctx(
            fieldday=fd,
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m", timestamp_offset_h=24)],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)

    def test_invalid_period_returns_error(self):
        fd = FieldDay()
        fd.name = "Bad"
        fd.start_utc = _utc(10)
        fd.end_utc = _utc(0)   # end before start
        fd.selected_bands = ["40m"]
        ctx = _ctx(fieldday=fd, stations=[_station("ON3VZ")])
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix, {})
        self.assertTrue(len(result.errors) > 0)

    def test_mixed_in_and_out_of_period(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[
                _qso("ON3VZ", "40m", timestamp_offset_h=-2),   # before → ignored
                _qso("ON3VZ", "40m", timestamp_offset_h=5),    # inside → counts
                _qso("ON3VZ", "80m", timestamp_offset_h=100),  # after → ignored
            ],
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON3VZ", "80m")].status, Status.NOT_WORKED)
        self.assertEqual(result.qsos_ignored_out_of_period, 2)
        self.assertEqual(result.qsos_in_period, 1)


# ---------------------------------------------------------------------------
# Business rule 3: Unknown callsigns are ignored
# ---------------------------------------------------------------------------

class TestUnknownCallsignsIgnored(unittest.TestCase):

    def test_unknown_callsign_ignored(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON9ZZZ", "40m")],  # not in station list
        )
        matrix, result = SyncEngine.recalculate(ctx)
        # ON9ZZZ should not appear in matrix
        self.assertNotIn(("ON9ZZZ", "40m"), matrix)
        self.assertEqual(result.qsos_ignored_unknown, 1)

    def test_known_callsign_not_ignored(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m")],
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(result.qsos_ignored_unknown, 0)

    def test_mix_known_and_unknown(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[
                _qso("ON3VZ", "40m"),   # known
                _qso("ON9ZZZ", "40m"),  # unknown → ignored
                _qso("ON8XXX", "80m"),  # unknown → ignored
            ],
        )
        _, result = SyncEngine.recalculate(ctx)
        self.assertEqual(result.qsos_ignored_unknown, 2)
        self.assertEqual(result.worked_combinations, 1)


# ---------------------------------------------------------------------------
# Business rule 4: Status per callsign + band
# ---------------------------------------------------------------------------

class TestCallsignBandKey(unittest.TestCase):

    def test_same_call_different_bands_independent(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m")],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON3VZ", "80m")].status, Status.NOT_WORKED)
        self.assertEqual(matrix[("ON3VZ", "160m")].status, Status.NOT_WORKED)

    def test_same_band_different_calls_independent(self):
        ctx = _ctx(
            stations=[_station("ON3VZ"), _station("ON4ABC")],
            qsos=[_qso("ON3VZ", "40m")],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(matrix[("ON4ABC", "40m")].status, Status.NOT_WORKED)


# ---------------------------------------------------------------------------
# Business rule 5: UTC timestamps
# ---------------------------------------------------------------------------

class TestUTCTimestamps(unittest.TestCase):

    def test_utc_aware_timestamp_in_period(self):
        fd = FieldDay()
        fd.name = "UTC_test"
        fd.start_utc = "2025-06-21T00:00:00+00:00"
        fd.end_utc   = "2025-06-22T00:00:00+00:00"
        fd.selected_bands = ["40m"]

        q = ReceivedQSO()
        q.original_callsign = "ON3VZ"
        q.normalized_callsign = "ON3VZ"
        q.band = "40m"
        q.timestamp_utc = "2025-06-21T12:00:00+00:00"  # UTC noon

        ctx = _ctx(fieldday=fd, stations=[_station("ON3VZ")], qsos=[q])
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)

    def test_naive_timestamp_treated_as_utc(self):
        """Timestamps without timezone info are assumed UTC."""
        fd = FieldDay()
        fd.name = "naive_ts"
        fd.start_utc = "2025-06-21T00:00:00+00:00"
        fd.end_utc   = "2025-06-22T00:00:00+00:00"
        fd.selected_bands = ["40m"]

        q = ReceivedQSO()
        q.original_callsign = "ON3VZ"
        q.normalized_callsign = "ON3VZ"
        q.band = "40m"
        q.timestamp_utc = "2025-06-21T12:00:00"  # no tz → assume UTC

        ctx = _ctx(fieldday=fd, stations=[_station("ON3VZ")], qsos=[q])
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)


# ---------------------------------------------------------------------------
# Business rule 6: Band derived from frequency
# ---------------------------------------------------------------------------

class TestBandFromFrequency(unittest.TestCase):

    def test_band_derived_from_frequency_when_band_missing(self):
        q = ReceivedQSO()
        q.original_callsign = "ON3VZ"
        q.normalized_callsign = "ON3VZ"
        q.band = ""                    # no band set
        q.frequency_hz = 7_030_000.0  # 40m
        q.timestamp_utc = _utc(5)
        q.n1mm_id = "freq-test"

        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[q],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)

    def test_unresolvable_band_skipped_with_error(self):
        q = ReceivedQSO()
        q.original_callsign = "ON3VZ"
        q.normalized_callsign = "ON3VZ"
        q.band = ""
        q.frequency_hz = None
        q.timestamp_utc = _utc(5)

        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[q],
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.NOT_WORKED)
        self.assertTrue(len(result.errors) > 0)


# ---------------------------------------------------------------------------
# Business rule 7: Strict / non-strict callsign matching
# ---------------------------------------------------------------------------

class TestCallsignMatchingModes(unittest.TestCase):

    def _qso_with_portable(self, call: str, band: str = "40m") -> ReceivedQSO:
        q = ReceivedQSO()
        q.original_callsign = call
        from app.core.callsign import normalize
        q.normalized_callsign = normalize(call, strict=False)
        q.band = band
        q.timestamp_utc = _utc(5)
        q.n1mm_id = f"{call}-{band}"
        return q

    def test_nonstrict_portable_matches_base(self):
        """ON3VZ/P matches station ON3VZ when strict=False."""
        q = self._qso_with_portable("ON3VZ/P")
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[q],
            strict=False,
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)
        self.assertEqual(result.qsos_ignored_unknown, 0)

    def test_strict_portable_does_not_match_base(self):
        """ON3VZ/P does NOT match station ON3VZ when strict=True."""
        from app.core.callsign import normalize
        q = ReceivedQSO()
        q.original_callsign = "ON3VZ/P"
        q.normalized_callsign = normalize("ON3VZ/P", strict=True)  # → "ON3VZ/P"
        q.band = "40m"
        q.timestamp_utc = _utc(5)
        q.n1mm_id = "strict-test"

        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[q],
            strict=True,
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.NOT_WORKED)
        self.assertEqual(result.qsos_ignored_unknown, 1)

    def test_nonstrict_qrp_matches_base(self):
        q = self._qso_with_portable("ON3VZ/QRP")
        ctx = _ctx(stations=[_station("ON3VZ")], qsos=[q], strict=False)
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)


# ---------------------------------------------------------------------------
# QSO details stored in matrix cell
# ---------------------------------------------------------------------------

class TestQSODetailsInMatrix(unittest.TestCase):

    def test_worked_timestamp_stored(self):
        q = _qso("ON3VZ", "40m", timestamp_offset_h=5, mode="SSB")
        ctx = _ctx(stations=[_station("ON3VZ")], qsos=[q])
        matrix, _ = SyncEngine.recalculate(ctx)
        cell = matrix[("ON3VZ", "40m")]
        self.assertEqual(cell.worked_timestamp_utc, q.timestamp_utc)
        self.assertEqual(cell.mode, "SSB")

    def test_most_recent_qso_wins_for_timestamp(self):
        q1 = _qso("ON3VZ", "40m", timestamp_offset_h=2)
        q2 = _qso("ON3VZ", "40m", timestamp_offset_h=8)  # more recent
        ctx = _ctx(stations=[_station("ON3VZ")], qsos=[q1, q2])
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix[("ON3VZ", "40m")].worked_timestamp_utc, q2.timestamp_utc)

    def test_frequency_stored(self):
        q = _qso("ON3VZ", "40m")
        q.frequency_hz = 7_030_000.0
        ctx = _ctx(stations=[_station("ON3VZ")], qsos=[q])
        matrix, _ = SyncEngine.recalculate(ctx)
        self.assertAlmostEqual(matrix[("ON3VZ", "40m")].frequency_hz, 7_030_000.0)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestSyncStatistics(unittest.TestCase):

    def test_counts_correct(self):
        ctx = _ctx(
            stations=[_station("ON3VZ"), _station("ON4ABC")],
            qsos=[
                _qso("ON3VZ", "40m"),
                _qso("ON3VZ", "80m"),
                # ON4ABC not worked on any band
            ],
        )
        matrix, result = SyncEngine.recalculate(ctx)
        # 2 stations × 3 bands = 6 cells; 2 worked, 4 unworked
        self.assertEqual(result.worked_combinations, 2)
        self.assertEqual(result.unworked_combinations, 4)
        self.assertEqual(result.total_qsos_processed, 2)

    def test_excluded_not_counted_as_worked_or_unworked(self):
        o = _override("ON3VZ", "40m", Status.EXCLUDED)
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m")],
            overrides={o.key: o},
        )
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(result.excluded_count, 1)
        self.assertEqual(result.worked_combinations, 0)
        self.assertEqual(result.unworked_combinations, 2)

    def test_no_selected_bands_returns_error(self):
        fd = _fieldday()
        fd.selected_bands = []
        ctx = _ctx(fieldday=fd, stations=[_station("ON3VZ")])
        matrix, result = SyncEngine.recalculate(ctx)
        self.assertEqual(matrix, {})
        self.assertTrue(len(result.errors) > 0)


# ---------------------------------------------------------------------------
# compute_station_statistics
# ---------------------------------------------------------------------------

class TestStationStatistics(unittest.TestCase):

    def test_fully_worked(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[
                _qso("ON3VZ", "40m"),
                _qso("ON3VZ", "80m"),
                _qso("ON3VZ", "160m"),
            ],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        stats = SyncEngine.compute_station_statistics(
            matrix, ctx.stations, ctx.fieldday.selected_bands
        )
        self.assertEqual(stats["fully_worked"], 1)
        self.assertEqual(stats["partially_worked"], 0)
        self.assertEqual(stats["not_worked"], 0)

    def test_partially_worked(self):
        ctx = _ctx(
            stations=[_station("ON3VZ")],
            qsos=[_qso("ON3VZ", "40m")],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        stats = SyncEngine.compute_station_statistics(
            matrix, ctx.stations, ctx.fieldday.selected_bands
        )
        self.assertEqual(stats["fully_worked"], 0)
        self.assertEqual(stats["partially_worked"], 1)
        self.assertEqual(stats["not_worked"], 0)

    def test_not_worked(self):
        ctx = _ctx(stations=[_station("ON3VZ")], qsos=[])
        matrix, _ = SyncEngine.recalculate(ctx)
        stats = SyncEngine.compute_station_statistics(
            matrix, ctx.stations, ctx.fieldday.selected_bands
        )
        self.assertEqual(stats["not_worked"], 1)

    def test_mixed_stations(self):
        ctx = _ctx(
            stations=[_station("ON3VZ"), _station("ON4ABC"), _station("ON5XY")],
            qsos=[
                # ON3VZ: all bands → fully worked
                _qso("ON3VZ", "40m"),
                _qso("ON3VZ", "80m"),
                _qso("ON3VZ", "160m"),
                # ON4ABC: one band → partially worked
                _qso("ON4ABC", "40m"),
                # ON5XY: no QSOs → not worked
            ],
        )
        matrix, _ = SyncEngine.recalculate(ctx)
        stats = SyncEngine.compute_station_statistics(
            matrix, ctx.stations, ctx.fieldday.selected_bands
        )
        self.assertEqual(stats["fully_worked"], 1)
        self.assertEqual(stats["partially_worked"], 1)
        self.assertEqual(stats["not_worked"], 1)


# ---------------------------------------------------------------------------
# process_single_qso (real-time update)
# ---------------------------------------------------------------------------

class TestProcessSingleQSO(unittest.TestCase):

    def _empty_matrix(self, stations, bands) -> dict:
        from app.core.models import StationBandStatus
        m = {}
        for s in stations:
            for b in bands:
                m[(s.normalized_callsign, b)] = StationBandStatus(
                    normalized_callsign=s.normalized_callsign,
                    band=b,
                    status=Status.NOT_WORKED,
                )
        return m

    def test_new_qso_updates_matrix(self):
        stations = [_station("ON3VZ")]
        ctx = _ctx(stations=stations)
        matrix = self._empty_matrix(stations, ["40m", "80m", "160m"])
        q = _qso("ON3VZ", "40m")
        matrix, changed = SyncEngine.process_single_qso(q, ctx, matrix)
        self.assertTrue(changed)
        self.assertEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)

    def test_already_worked_not_changed(self):
        stations = [_station("ON3VZ")]
        ctx = _ctx(stations=stations)
        matrix = self._empty_matrix(stations, ["40m", "80m", "160m"])
        matrix[("ON3VZ", "40m")].status = Status.WORKED_BY_N1MM
        q = _qso("ON3VZ", "40m")
        matrix, changed = SyncEngine.process_single_qso(q, ctx, matrix)
        self.assertFalse(changed)

    def test_override_prevents_realtime_update(self):
        o = _override("ON3VZ", "40m", Status.MANUAL_NOT_WORKED)
        stations = [_station("ON3VZ")]
        ctx = _ctx(stations=stations, overrides={o.key: o})
        matrix = self._empty_matrix(stations, ["40m", "80m", "160m"])
        q = _qso("ON3VZ", "40m")
        matrix, changed = SyncEngine.process_single_qso(q, ctx, matrix)
        self.assertFalse(changed)
        # Status should NOT have changed to worked
        self.assertNotEqual(matrix[("ON3VZ", "40m")].status, Status.WORKED_BY_N1MM)

    def test_unknown_callsign_no_change(self):
        stations = [_station("ON3VZ")]
        ctx = _ctx(stations=stations)
        matrix = self._empty_matrix(stations, ["40m", "80m", "160m"])
        q = _qso("ON9ZZZ", "40m")
        matrix, changed = SyncEngine.process_single_qso(q, ctx, matrix)
        self.assertFalse(changed)

    def test_out_of_period_no_change(self):
        stations = [_station("ON3VZ")]
        ctx = _ctx(stations=stations)
        matrix = self._empty_matrix(stations, ["40m", "80m", "160m"])
        q = _qso("ON3VZ", "40m", timestamp_offset_h=-5)  # before period
        matrix, changed = SyncEngine.process_single_qso(q, ctx, matrix)
        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
