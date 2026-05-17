"""
app/core/sync_engine.py
=======================
Sync engine for N1MM Field Day Tracker.

This module contains **all** the business logic for computing the
station × band status matrix.  It has zero UI dependencies and can be
called from the background UDP listener thread, the manual sync button,
or a test.

Critical business rules (enforced here)
----------------------------------------
1. Manual override wins — always, unconditionally.
2. QSOs outside the field day period are ignored.
3. Unknown callsigns (not in the station list) are ignored.
4. Status is per callsign + band (not per QSO count).
5. All timestamps are compared in UTC.
6. Band is derived from frequency when not explicitly provided.
7. Strict callsign matching is configurable.

Public API
----------
SyncEngine.recalculate(context) → SyncResult
SyncContext                     – input bundle (no UI refs)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.callsign import normalize
from app.core.matching import find_station, resolve_band
from app.core.models import (
    FieldDay,
    Override,
    ReceivedQSO,
    Station,
    StationBandStatus,
    SyncResult,
)
from app.core.status import Status

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SyncContext — all inputs in one place
# ---------------------------------------------------------------------------

@dataclass
class SyncContext:
    """Everything the sync engine needs to compute the matrix.

    Parameters
    ----------
    fieldday:
        The active field day (provides period and selected_bands).
    stations:
        All participating stations (imported + manually added).
    qsos:
        All QSOs received from N1MM and stored locally.
    overrides:
        Manual overrides keyed by ``(normalized_callsign, band)``.
    strict:
        Callsign matching mode.
    """

    fieldday: FieldDay
    stations: list[Station] = field(default_factory=list)
    qsos: list[ReceivedQSO] = field(default_factory=list)
    overrides: dict[tuple[str, str], Override] = field(default_factory=dict)
    strict: bool = False


# ---------------------------------------------------------------------------
# SyncEngine
# ---------------------------------------------------------------------------

class SyncEngine:
    """Stateless service that computes the station × band matrix.

    All state is passed in via :class:`SyncContext` and returned in
    the result dicts.  Nothing is persisted here — callers save the
    results via the repository.
    """

    @staticmethod
    def recalculate(ctx: SyncContext) -> tuple[
        dict[tuple[str, str], StationBandStatus],
        SyncResult,
    ]:
        """Compute the full station × band status matrix from scratch.

        Parameters
        ----------
        ctx:
            All input data needed for the computation.

        Returns
        -------
        (matrix, result)
            ``matrix`` maps ``(normalized_callsign, band)`` →
            :class:`~app.core.models.StationBandStatus`.

            ``result`` is a :class:`~app.core.models.SyncResult` with
            statistics and any non-fatal errors encountered.
        """
        result = SyncResult()
        matrix: dict[tuple[str, str], StationBandStatus] = {}

        # ── Guard: no field day period ───────────────────────────────
        if not ctx.fieldday.is_valid_period():
            result.errors.append(
                "Field day has no valid period (start/end not set or end ≤ start)."
            )
            log.warning("Sync skipped: invalid field day period.")
            return matrix, result

        selected_bands: set[str] = set(ctx.fieldday.selected_bands)
        if not selected_bands:
            result.errors.append("No bands selected for this field day.")
            log.warning("Sync skipped: no bands selected.")
            return matrix, result

        # ── Build station lookup ─────────────────────────────────────
        station_map: dict[str, Station] = {
            s.normalized_callsign: s for s in ctx.stations
        }

        # ── Step 1: initialise matrix with NOT_WORKED ────────────────
        # Every station × selected_band combination starts as not_worked.
        for station in ctx.stations:
            for band in selected_bands:
                key = (station.normalized_callsign, band)
                matrix[key] = StationBandStatus(
                    normalized_callsign=station.normalized_callsign,
                    band=band,
                    status=Status.NOT_WORKED,
                    has_override=False,
                )

        # ── Step 2: process QSOs ─────────────────────────────────────
        # Track the "best" (most recent) worked QSO per (callsign, band)
        # so we can store the timestamp, mode and frequency.
        worked_qsos: dict[tuple[str, str], ReceivedQSO] = {}

        for qso in ctx.qsos:
            result.total_qsos_processed += 1

            # Period filter
            if not ctx.fieldday.qso_in_period(qso.timestamp_utc):
                result.qsos_ignored_out_of_period += 1
                log.debug(
                    "QSO %s @ %s outside period — ignored.",
                    qso.original_callsign, qso.timestamp_utc,
                )
                continue

            result.qsos_in_period += 1

            # Normalise callsign
            norm_call = normalize(qso.original_callsign, strict=ctx.strict)

            # Station lookup — unknown callsigns are ignored
            station = find_station(norm_call, station_map, strict=ctx.strict)
            if station is None:
                result.qsos_ignored_unknown += 1
                log.debug(
                    "QSO callsign %s not in station list — ignored.", norm_call
                )
                continue

            # Band resolution
            band = resolve_band(qso)
            if band is None:
                result.errors.append(
                    f"Could not determine band for QSO from {qso.original_callsign} "
                    f"(band={qso.band!r}, freq={qso.frequency_hz}). Skipped."
                )
                continue

            # Skip bands not selected for this field day
            if band not in selected_bands:
                log.debug(
                    "QSO %s on band %s not in selected bands — ignored.",
                    norm_call, band,
                )
                continue

            # Mark as worked
            key = (station.normalized_callsign, band)
            if key not in matrix:
                # Band was added to selected_bands after QSO was received
                matrix[key] = StationBandStatus(
                    normalized_callsign=station.normalized_callsign,
                    band=band,
                    status=Status.NOT_WORKED,
                )

            matrix[key].status = Status.WORKED_BY_N1MM

            # Keep most recent QSO for this key (for timestamp/mode/freq display)
            existing = worked_qsos.get(key)
            if existing is None or qso.timestamp_utc >= existing.timestamp_utc:
                worked_qsos[key] = qso

        # ── Step 3: enrich matrix with QSO details ───────────────────
        for key, qso in worked_qsos.items():
            if key in matrix:
                matrix[key].worked_timestamp_utc = qso.timestamp_utc
                matrix[key].mode = qso.mode
                matrix[key].frequency_hz = qso.frequency_hz

        # ── Step 4: apply manual overrides (always win) ──────────────
        for key, override in ctx.overrides.items():
            norm_call, band = key

            # Ensure there is a matrix cell for this override
            if key not in matrix:
                # Could be for a band not currently selected, or a station
                # not currently in the list — create a placeholder
                log.debug(
                    "Override for (%s, %s) has no matrix cell; creating placeholder.",
                    norm_call, band,
                )
                matrix[key] = StationBandStatus(
                    normalized_callsign=norm_call,
                    band=band,
                    status=Status.NOT_WORKED,
                )

            try:
                new_status = Status(override.status)
            except ValueError:
                result.errors.append(
                    f"Unknown override status '{override.status}' for "
                    f"({norm_call}, {band}) — skipped."
                )
                log.warning(
                    "Invalid override status '%s' for (%s, %s)",
                    override.status, norm_call, band,
                )
                continue

            matrix[key].status = new_status
            matrix[key].has_override = True
            result.manual_override_count += 1

        # ── Step 5: compute summary statistics ───────────────────────
        worked_count = 0
        unworked_count = 0
        excluded_count = 0

        for key, cell in matrix.items():
            norm_call, band = key
            # Only count cells for currently selected bands and known stations
            if band not in selected_bands:
                continue
            if norm_call not in station_map:
                continue

            if cell.status.is_excluded():
                excluded_count += 1
            elif cell.status.is_worked():
                worked_count += 1
            else:
                unworked_count += 1

        result.worked_combinations = worked_count
        result.unworked_combinations = unworked_count
        result.excluded_count = excluded_count

        log.info(
            "Sync complete: %d QSOs processed, %d in period, "
            "%d unknown, %d out-of-period | "
            "%d worked, %d unworked, %d excluded, %d overrides",
            result.total_qsos_processed,
            result.qsos_in_period,
            result.qsos_ignored_unknown,
            result.qsos_ignored_out_of_period,
            result.worked_combinations,
            result.unworked_combinations,
            result.excluded_count,
            result.manual_override_count,
        )

        return matrix, result

    @staticmethod
    def compute_station_statistics(
        matrix: dict[tuple[str, str], StationBandStatus],
        stations: list[Station],
        selected_bands: list[str],
    ) -> dict[str, int]:
        """Compute per-station summary statistics from a computed matrix.

        Parameters
        ----------
        matrix:
            Output of :meth:`recalculate`.
        stations:
            Participating stations.
        selected_bands:
            Bands active for this field day.

        Returns
        -------
        dict with keys:
            ``fully_worked``, ``partially_worked``, ``not_worked``
        """
        fully_worked = 0
        partially_worked = 0
        not_worked_stations = 0
        bands = set(selected_bands)

        for station in stations:
            nc = station.normalized_callsign
            cells = [
                matrix.get((nc, band))
                for band in bands
            ]
            cells = [c for c in cells if c is not None]

            if not cells:
                not_worked_stations += 1
                continue

            worked = sum(1 for c in cells if c.status.is_worked())
            excluded = sum(1 for c in cells if c.status.is_excluded())
            active = len(cells) - excluded

            if active == 0:
                # All excluded
                not_worked_stations += 1
            elif worked == active:
                fully_worked += 1
            elif worked > 0:
                partially_worked += 1
            else:
                not_worked_stations += 1

        return {
            "fully_worked": fully_worked,
            "partially_worked": partially_worked,
            "not_worked": not_worked_stations,
        }

    @staticmethod
    def process_single_qso(
        qso: ReceivedQSO,
        ctx: SyncContext,
        matrix: dict[tuple[str, str], StationBandStatus],
    ) -> tuple[dict[tuple[str, str], StationBandStatus], bool]:
        """Process a single newly received QSO and update *matrix* in place.

        Used by the real-time UDP listener to update the matrix without
        a full recalculate pass.

        Parameters
        ----------
        qso:
            The newly received QSO.
        ctx:
            Current sync context (field day, stations, overrides, strict).
        matrix:
            The current matrix (modified in place).

        Returns
        -------
        (matrix, changed)
            ``changed`` is True if any cell status changed.
        """
        changed = False

        if not ctx.fieldday.is_valid_period():
            return matrix, changed

        selected_bands: set[str] = set(ctx.fieldday.selected_bands)
        station_map: dict[str, Station] = {
            s.normalized_callsign: s for s in ctx.stations
        }

        # Period check
        if not ctx.fieldday.qso_in_period(qso.timestamp_utc):
            log.debug("Real-time QSO outside period — ignored.")
            return matrix, changed

        # Station lookup
        norm_call = normalize(qso.original_callsign, strict=ctx.strict)
        station = find_station(norm_call, station_map, strict=ctx.strict)
        if station is None:
            log.debug("Real-time QSO callsign %s unknown — ignored.", norm_call)
            return matrix, changed

        # Band
        band = resolve_band(qso)
        if band is None or band not in selected_bands:
            return matrix, changed

        key = (station.normalized_callsign, band)

        # Only update if not overridden
        override = ctx.overrides.get(key)
        if override is not None:
            log.debug(
                "Real-time QSO (%s, %s) has manual override — not changing status.",
                station.normalized_callsign, band,
            )
            return matrix, changed

        # Ensure matrix cell exists
        if key not in matrix:
            matrix[key] = StationBandStatus(
                normalized_callsign=station.normalized_callsign,
                band=band,
                status=Status.NOT_WORKED,
            )

        if matrix[key].status != Status.WORKED_BY_N1MM:
            matrix[key].status = Status.WORKED_BY_N1MM
            matrix[key].worked_timestamp_utc = qso.timestamp_utc
            matrix[key].mode = qso.mode
            matrix[key].frequency_hz = qso.frequency_hz
            changed = True
            log.info(
                "Matrix updated: %s + %s → worked_by_n1mm",
                station.normalized_callsign, band,
            )

        return matrix, changed
