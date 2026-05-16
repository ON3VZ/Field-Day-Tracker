"""
app/importers/csv_importer.py
==============================
CSV station import for N1MM Field Day Tracker.

CSV format
----------
Required column : ``callsign``
Optional columns: ``name``, ``club``, ``remarks``

The file may use any delimiter that Python's csv.Sniffer can detect
(comma is the default).  A header row is required.  Extra columns are
silently ignored.

Example::

    callsign,name,club,remarks
    ON3VZ,Cornelis,WLD,
    ON4ABC,,,
    ON5XY,Jan,UBA,Club secretary

Re-import rules
---------------
When a CSV is imported into a field day that already has stations:

1. Callsigns that exist in the new CSV → kept (data updated from CSV).
2. Callsigns that were *manually* added (``source == "manual"``) → kept
   unless the user explicitly requests removal.
3. Callsigns that existed in the old CSV but are *absent* from the new CSV
   → returned in ``ImportResult.removed_callsigns`` so the UI can warn the
   user before deleting them.
4. Manual overrides are never touched by the importer — they live in
   ``overrides.json`` and are managed separately.

Public API
----------
CSVImporter.import_csv(path, existing_stations, strict)
    → ImportResult
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.core.callsign import is_valid_callsign, normalize
from app.core.models import Station

log = logging.getLogger(__name__)

# Column names we recognise (all lower-cased before matching)
_COL_CALLSIGN = "callsign"
_COL_NAME = "name"
_COL_CLUB = "club"
_COL_REMARKS = "remarks"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ImportResult:
    """Result of a CSV import operation.

    Attributes
    ----------
    stations:
        The full merged station list to be saved to disk.
    added:
        Callsigns that are new (not previously in the station list).
    updated:
        Callsigns that existed and had their CSV data refreshed.
    skipped_invalid:
        Raw callsign strings that failed validation and were skipped.
    skipped_duplicate:
        Callsigns that appeared more than once in the CSV (only the first
        occurrence is kept).
    removed_callsigns:
        CSV-sourced callsigns from the *old* list that are absent from the
        new CSV.  The UI must ask the user before actually removing them.
    manually_added_kept:
        Manually added callsigns that were retained unchanged.
    errors:
        Non-fatal error messages (e.g. unreadable rows).
    total_csv_rows:
        Total data rows read from the CSV (excluding header).
    """

    stations: list[Station] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped_invalid: list[str] = field(default_factory=list)
    skipped_duplicate: list[str] = field(default_factory=list)
    removed_callsigns: list[str] = field(default_factory=list)
    manually_added_kept: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_csv_rows: int = 0

    @property
    def success(self) -> bool:
        """True if at least one station was imported."""
        return bool(self.stations)

    @property
    def summary(self) -> str:
        """One-line human-readable summary."""
        return (
            f"Imported {len(self.added)} new, "
            f"{len(self.updated)} updated, "
            f"{len(self.skipped_invalid)} invalid, "
            f"{len(self.removed_callsigns)} removed from CSV."
        )


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------

class CSVImporter:
    """Stateless service that parses a station CSV file.

    All state lives in the returned :class:`ImportResult`.
    """

    @staticmethod
    def import_csv(
        path: Path | str,
        existing_stations: list[Station] | None = None,
        *,
        strict: bool = False,
    ) -> ImportResult:
        """Parse *path* and merge with *existing_stations*.

        Parameters
        ----------
        path:
            Path to the CSV file.
        existing_stations:
            Current station list loaded from ``stations.json``.
            Pass ``None`` or ``[]`` for a fresh import.
        strict:
            Callsign normalisation mode.  Passed through to
            :func:`app.core.callsign.normalize`.

        Returns
        -------
        ImportResult
            Contains the merged station list and a full accounting of what
            happened.  The caller is responsible for saving the result to
            disk and for acting on ``removed_callsigns`` (with user
            confirmation).
        """
        path = Path(path)
        result = ImportResult()
        existing_stations = existing_stations or []

        # --- Read CSV ---
        try:
            csv_rows = _read_csv(path, result)
        except OSError as exc:
            result.errors.append(f"Cannot open file: {exc}")
            log.error("CSV import failed: %s", exc)
            return result

        if not csv_rows:
            result.errors.append("No valid data rows found in CSV.")
            return result

        # --- Build lookup of existing stations ---
        # Key: normalized_callsign → Station
        existing_map: dict[str, Station] = {
            s.normalized_callsign: s for s in existing_stations
        }

        # --- Process CSV rows ---
        seen_in_csv: set[str] = set()   # normalised callsigns seen in this CSV
        merged: dict[str, Station] = {} # result map: norm_call → Station

        for row in csv_rows:
            result.total_csv_rows += 1
            raw_call = row.get(_COL_CALLSIGN, "").strip()

            # Validate
            if not is_valid_callsign(raw_call):
                log.debug("Skipping invalid callsign: %r", raw_call)
                result.skipped_invalid.append(raw_call)
                continue

            norm_call = normalize(raw_call, strict=strict)

            # Deduplicate within CSV
            if norm_call in seen_in_csv:
                log.debug("Duplicate callsign in CSV: %s", norm_call)
                result.skipped_duplicate.append(norm_call)
                continue
            seen_in_csv.add(norm_call)

            # Build Station
            if norm_call in existing_map:
                # Update existing CSV-sourced station with fresh CSV data
                station = existing_map[norm_call]
                if station.source == "csv":
                    station.name = row.get(_COL_NAME, station.name).strip()
                    station.club = row.get(_COL_CLUB, station.club).strip()
                    # Preserve existing remarks if CSV column is empty
                    csv_remarks = row.get(_COL_REMARKS, "").strip()
                    if csv_remarks:
                        station.remarks = csv_remarks
                    station.callsign = raw_call
                    station.normalized_callsign = norm_call
                    result.updated.append(norm_call)
                    log.debug("Updated station: %s", norm_call)
                else:
                    # Manually added station also matches this CSV call →
                    # keep it but mark as updated
                    result.updated.append(norm_call)
            else:
                # New station from CSV
                station = Station(
                    callsign=raw_call,
                    normalized_callsign=norm_call,
                    name=row.get(_COL_NAME, "").strip(),
                    club=row.get(_COL_CLUB, "").strip(),
                    remarks=row.get(_COL_REMARKS, "").strip(),
                    source="csv",
                )
                result.added.append(norm_call)
                log.debug("Added station: %s", norm_call)

            merged[norm_call] = station

        # --- Handle existing stations not in new CSV ---
        for norm_call, station in existing_map.items():
            if norm_call in merged:
                continue  # already processed

            if station.source == "manual":
                # Always keep manually added stations
                merged[norm_call] = station
                result.manually_added_kept.append(norm_call)
                log.debug("Kept manually added station: %s", norm_call)
            else:
                # CSV-sourced station missing from new CSV → flag for user
                # Still include in result so the UI can show it before asking
                merged[norm_call] = station
                result.removed_callsigns.append(norm_call)
                log.debug(
                    "Station %s no longer in CSV (flagged for removal)", norm_call
                )

        # --- Preserve original order: existing first, new at end ---
        final_stations: list[Station] = []
        # First: existing stations that are still present (preserves original order)
        for s in existing_stations:
            if s.normalized_callsign in merged:
                final_stations.append(merged.pop(s.normalized_callsign))
        # Then: newly added stations (in CSV order)
        for norm_call in result.added:
            if norm_call in merged:
                final_stations.append(merged.pop(norm_call))

        result.stations = final_stations

        log.info(
            "CSV import complete: %d added, %d updated, %d invalid, %d removed",
            len(result.added),
            len(result.updated),
            len(result.skipped_invalid),
            len(result.removed_callsigns),
        )
        return result

    @staticmethod
    def apply_removals(
        stations: list[Station],
        callsigns_to_remove: list[str],
    ) -> list[Station]:
        """Remove stations whose normalised callsign is in *callsigns_to_remove*.

        Call this after the user confirms removal of missing CSV stations.

        Parameters
        ----------
        stations:
            Current station list.
        callsigns_to_remove:
            Normalised callsigns to remove (from ``ImportResult.removed_callsigns``).

        Returns
        -------
        list[Station]
            Filtered station list.
        """
        remove_set = set(callsigns_to_remove)
        result = [s for s in stations if s.normalized_callsign not in remove_set]
        log.info(
            "Removed %d stations: %s",
            len(stations) - len(result),
            callsigns_to_remove,
        )
        return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_csv(path: Path, result: ImportResult) -> list[dict[str, str]]:
    """Read CSV rows into a list of dicts with lowercased keys.

    Validates that the ``callsign`` column is present.
    Populates ``result.errors`` for non-fatal issues.

    Raises
    ------
    OSError
        If the file cannot be opened.
    """
    rows: list[dict[str, str]] = []

    with path.open(newline="", encoding="utf-8-sig") as fh:
        # Detect delimiter
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel  # fall back to comma

        reader = csv.DictReader(fh, dialect=dialect)

        # Validate header
        if reader.fieldnames is None:
            result.errors.append("CSV file appears to be empty.")
            return rows

        # Normalise column names to lower-case for comparison
        lower_fields = [f.lower().strip() for f in reader.fieldnames]
        if _COL_CALLSIGN not in lower_fields:
            result.errors.append(
                f"CSV is missing the required '{_COL_CALLSIGN}' column. "
                f"Found columns: {list(reader.fieldnames)}"
            )
            return rows

        # Build a normalised-key reader
        for i, row in enumerate(reader, start=2):  # line 2 = first data row
            try:
                normalised = {k.lower().strip(): (v or "").strip() for k, v in row.items()}
                rows.append(normalised)
            except Exception as exc:  # noqa: BLE001
                msg = f"Row {i}: skipped due to error ({exc})"
                result.errors.append(msg)
                log.warning("CSV row error: %s", msg)

    return rows
