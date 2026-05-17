"""
app/exporters/csv_exporter.py
==============================
CSV export for N1MM Field Day Tracker.

Exports the full station × band status matrix to a CSV file.

Output columns
--------------
callsign, normalized_callsign, band, status, source,
mode, frequency_mhz, worked_timestamp_utc, manual_override, remarks

One row per station × band combination.
Rows are sorted: callsign A→Z, then band in band-plan order.

Public API
----------
CSVExporter.export(path, fieldday, stations, matrix)  → ExportResult
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.band_plan import ordered_band_names
from app.core.models import FieldDay, Station, StationBandStatus
from app.core.status import Status
from app.storage.json_store import ensure_dir

log = logging.getLogger(__name__)

# CSV column headers (always English — these are data headers, not UI)
_HEADERS = [
    "callsign",
    "normalized_callsign",
    "band",
    "status",
    "source",
    "mode",
    "frequency_mhz",
    "worked_timestamp_utc",
    "manual_override",
    "remarks",
]


@dataclass
class ExportResult:
    """Result of an export operation."""
    path: Path
    rows_written: int
    success: bool
    error: str = ""


class CSVExporter:
    """Stateless CSV exporter."""

    @staticmethod
    def export(
        path: Path,
        fieldday: FieldDay,
        stations: list[Station],
        matrix: dict[tuple[str, str], StationBandStatus],
    ) -> ExportResult:
        """Write the matrix to *path* as CSV.

        Parameters
        ----------
        path:
            Destination file path.  Parent directories are created.
        fieldday:
            Active field day (provides selected bands).
        stations:
            Participating stations.
        matrix:
            Current computed matrix from the sync engine.

        Returns
        -------
        ExportResult
        """
        path = Path(path)
        ensure_dir(path.parent)

        bands = ordered_band_names(fieldday.selected_bands)
        station_map = {s.normalized_callsign: s for s in stations}

        # Build rows: one per (station, band)
        rows: list[dict] = []
        for station in sorted(stations, key=lambda s: s.normalized_callsign):
            nc = station.normalized_callsign
            for band in bands:
                key = (nc, band)
                cell = matrix.get(key)
                status_val = cell.status.value if cell else Status.NOT_WORKED.value
                is_override = cell.has_override if cell else False

                # Frequency: convert Hz → MHz
                freq_mhz = ""
                if cell and cell.frequency_hz is not None:
                    freq_mhz = f"{cell.frequency_hz / 1_000_000:.4f}"

                worked_ts = ""
                if cell and cell.worked_timestamp_utc:
                    worked_ts = cell.worked_timestamp_utc

                rows.append({
                    "callsign":             station.callsign,
                    "normalized_callsign":  nc,
                    "band":                 band,
                    "status":               status_val,
                    "source":               station.source,
                    "mode":                 (cell.mode if cell else ""),
                    "frequency_mhz":        freq_mhz,
                    "worked_timestamp_utc": worked_ts,
                    "manual_override":      "yes" if is_override else "no",
                    "remarks":              station.remarks or "",
                })

        try:
            with path.open("w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=_HEADERS)
                writer.writeheader()
                writer.writerows(rows)

            log.info("CSV export: %d rows → %s", len(rows), path)
            return ExportResult(path=path, rows_written=len(rows), success=True)

        except OSError as exc:
            log.error("CSV export failed: %s", exc)
            return ExportResult(
                path=path, rows_written=0, success=False, error=str(exc)
            )

    @staticmethod
    def default_filename(fieldday: FieldDay) -> str:
        """Return a default filename for the export."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = fieldday.name.replace(" ", "_")
        return f"{safe_name}_export_{ts}.csv"
