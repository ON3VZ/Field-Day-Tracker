"""
app/storage/fieldday_repository.py
====================================
Repository for all field day data stored on disk.

Folder layout (one folder per field day)
-----------------------------------------
::

    <app_root>/
    ├── app_settings.json
    └── fielddays/
        └── <fieldday_name>/
            ├── fieldday.json
            ├── stations.json
            ├── received_qsos.json
            ├── overrides.json
            ├── sync_log.json
            └── exports/

All reads/writes go through ``json_store`` for atomic, safe I/O.

Public classes
--------------
FieldDayRepository   – manages one field day folder
AppSettingsRepository – manages app_settings.json
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.models import (
    AppSettings,
    FieldDay,
    Override,
    ReceivedQSO,
    Station,
)
from app.storage.json_store import (
    ensure_dir,
    read_json_dict,
    read_json_list,
    write_json,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FIELDDAYS_DIR = "fielddays"
_SETTINGS_FILE = "app_settings.json"

_FILE_FIELDDAY = "fieldday.json"
_FILE_STATIONS = "stations.json"
_FILE_QSOS = "received_qsos.json"
_FILE_OVERRIDES = "overrides.json"
_FILE_SYNC_LOG = "sync_log.json"
_DIR_EXPORTS = "exports"

# Valid field day name: letters, digits, underscore, hyphen (no spaces, no slashes)
_VALID_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_valid_fieldday_name(name: str) -> bool:
    """Return True if *name* is a valid field day folder name."""
    return bool(name) and bool(_VALID_NAME_RE.match(name))


# ---------------------------------------------------------------------------
# AppSettingsRepository
# ---------------------------------------------------------------------------

class AppSettingsRepository:
    """Reads and writes ``app_settings.json`` in the application root.

    Parameters
    ----------
    app_root:
        The directory where ``app_settings.json`` lives.
    """

    def __init__(self, app_root: Path) -> None:
        self._path = Path(app_root) / _SETTINGS_FILE

    def load(self) -> AppSettings:
        """Load settings from disk.  Returns defaults if file is missing."""
        data = read_json_dict(self._path)
        if data:
            log.debug("Loaded app settings from %s", self._path)
        else:
            log.info("No app settings found at %s – using defaults.", self._path)
        return AppSettings.from_dict(data)

    def save(self, settings: AppSettings) -> None:
        """Persist *settings* to disk."""
        write_json(self._path, settings.to_dict())
        log.debug("Saved app settings to %s", self._path)

    def set_last_active(self, fieldday_name: Optional[str], settings: AppSettings) -> None:
        """Update and persist the last active field day name."""
        settings.last_active_fieldday = fieldday_name
        self.save(settings)


# ---------------------------------------------------------------------------
# FieldDayRepository
# ---------------------------------------------------------------------------

class FieldDayRepository:
    """Repository for all data belonging to a single field day.

    Parameters
    ----------
    app_root:
        The application root directory (contains ``fielddays/``).
    fieldday_name:
        The field day folder name (must pass :func:`is_valid_fieldday_name`).
    """

    def __init__(self, app_root: Path, fieldday_name: str) -> None:
        if not is_valid_fieldday_name(fieldday_name):
            raise ValueError(
                f"Invalid field day name: {fieldday_name!r}. "
                "Use only letters, digits, underscore and hyphen."
            )
        self._root = Path(app_root) / _FIELDDAYS_DIR / fieldday_name
        self._name = fieldday_name
        ensure_dir(self._root)
        ensure_dir(self._root / _DIR_EXPORTS)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def folder(self) -> Path:
        """Absolute path to this field day's data folder."""
        return self._root

    @property
    def exports_folder(self) -> Path:
        """Absolute path to the exports subfolder."""
        return self._root / _DIR_EXPORTS

    def _path(self, filename: str) -> Path:
        return self._root / filename

    # ------------------------------------------------------------------
    # FieldDay metadata
    # ------------------------------------------------------------------

    def load_fieldday(self) -> FieldDay:
        """Load field day metadata.  Returns a new FieldDay if missing."""
        data = read_json_dict(self._path(_FILE_FIELDDAY))
        if data:
            fd = FieldDay.from_dict(data)
            log.debug("Loaded field day: %s", fd.name)
            return fd
        # Return a skeleton with the correct name
        fd = FieldDay()
        fd.name = self._name
        return fd

    def save_fieldday(self, fieldday: FieldDay) -> None:
        """Persist field day metadata."""
        fieldday.touch()
        write_json(self._path(_FILE_FIELDDAY), fieldday.to_dict())
        log.debug("Saved field day: %s", fieldday.name)

    # ------------------------------------------------------------------
    # Stations
    # ------------------------------------------------------------------

    def load_stations(self) -> list[Station]:
        """Load all stations (CSV-imported + manually added)."""
        raw = read_json_list(self._path(_FILE_STATIONS))
        stations = [Station.from_dict(d) for d in raw if isinstance(d, dict)]
        log.debug("Loaded %d stations for %s", len(stations), self._name)
        return stations

    def save_stations(self, stations: list[Station]) -> None:
        """Persist the full station list."""
        write_json(self._path(_FILE_STATIONS), [s.to_dict() for s in stations])
        log.debug("Saved %d stations for %s", len(stations), self._name)

    def add_station(self, station: Station, stations: list[Station]) -> list[Station]:
        """Add *station* to *stations* if not already present (by normalised callsign).

        Returns the updated list (does not auto-save — caller must call
        :meth:`save_stations`).
        """
        existing_calls = {s.normalized_callsign for s in stations}
        if station.normalized_callsign in existing_calls:
            log.debug(
                "Station %s already exists, skipping add.", station.normalized_callsign
            )
            return stations
        stations.append(station)
        log.debug("Added station: %s", station.normalized_callsign)
        return stations

    def station_map(self, stations: list[Station]) -> dict[str, Station]:
        """Return a dict keyed by ``normalized_callsign`` for fast lookup."""
        return {s.normalized_callsign: s for s in stations}

    # ------------------------------------------------------------------
    # Received QSOs
    # ------------------------------------------------------------------

    def load_qsos(self) -> list[ReceivedQSO]:
        """Load all received QSOs from disk."""
        raw = read_json_list(self._path(_FILE_QSOS))
        qsos = [ReceivedQSO.from_dict(d) for d in raw if isinstance(d, dict)]
        log.debug("Loaded %d QSOs for %s", len(qsos), self._name)
        return qsos

    def save_qsos(self, qsos: list[ReceivedQSO]) -> None:
        """Persist the full QSO list."""
        write_json(self._path(_FILE_QSOS), [q.to_dict() for q in qsos])
        log.debug("Saved %d QSOs for %s", len(qsos), self._name)

    def append_qso(self, qso: ReceivedQSO, existing: list[ReceivedQSO]) -> list[ReceivedQSO]:
        """Append *qso* to *existing*, deduplicating by ``n1mm_id`` if set.

        Returns the updated list.  Caller must call :meth:`save_qsos`.
        """
        if qso.n1mm_id:
            ids = {q.n1mm_id for q in existing if q.n1mm_id}
            if qso.n1mm_id in ids:
                log.debug("Duplicate QSO id=%s, skipping.", qso.n1mm_id)
                return existing
        existing.append(qso)
        return existing

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def load_overrides(self) -> dict[tuple[str, str], Override]:
        """Load all manual overrides.

        Returns
        -------
        dict keyed by ``(normalized_callsign, band)`` tuples.
        """
        raw = read_json_list(self._path(_FILE_OVERRIDES))
        result: dict[tuple[str, str], Override] = {}
        for d in raw:
            if not isinstance(d, dict):
                continue
            o = Override.from_dict(d)
            if o.normalized_callsign and o.band:
                result[o.key] = o
        log.debug("Loaded %d overrides for %s", len(result), self._name)
        return result

    def save_overrides(self, overrides: dict[tuple[str, str], Override]) -> None:
        """Persist all overrides."""
        write_json(
            self._path(_FILE_OVERRIDES),
            [o.to_dict() for o in overrides.values()],
        )
        log.debug("Saved %d overrides for %s", len(overrides), self._name)

    def set_override(
        self,
        overrides: dict[tuple[str, str], Override],
        override: Override,
    ) -> dict[tuple[str, str], Override]:
        """Add or replace an override.  Returns updated dict (does not save)."""
        overrides[override.key] = override
        return overrides

    def clear_override(
        self,
        overrides: dict[tuple[str, str], Override],
        normalized_callsign: str,
        band: str,
    ) -> dict[tuple[str, str], Override]:
        """Remove an override if present.  Returns updated dict (does not save)."""
        key = (normalized_callsign, band)
        if key in overrides:
            del overrides[key]
            log.debug("Cleared override for %s + %s", normalized_callsign, band)
        return overrides

    # ------------------------------------------------------------------
    # Sync log
    # ------------------------------------------------------------------

    def append_sync_log(self, entry: dict) -> None:
        """Append a sync log entry.  Keeps the last 100 entries."""
        existing = read_json_list(self._path(_FILE_SYNC_LOG))
        entry.setdefault("timestamp_utc", _utcnow())
        existing.append(entry)
        # Keep last 100 entries to avoid unbounded growth
        if len(existing) > 100:
            existing = existing[-100:]
        write_json(self._path(_FILE_SYNC_LOG), existing)

    def load_sync_log(self) -> list[dict]:
        """Load sync log entries."""
        return read_json_list(self._path(_FILE_SYNC_LOG))

    # ------------------------------------------------------------------
    # Existence / discovery
    # ------------------------------------------------------------------

    @classmethod
    def list_fielddays(cls, app_root: Path) -> list[str]:
        """Return sorted list of field day names found on disk.

        A field day is considered valid if its directory contains a
        ``fieldday.json`` file.
        """
        fd_root = Path(app_root) / _FIELDDAYS_DIR
        if not fd_root.exists():
            return []
        names = []
        for entry in sorted(fd_root.iterdir()):
            if entry.is_dir() and (entry / _FILE_FIELDDAY).exists():
                names.append(entry.name)
        return names

    @classmethod
    def exists(cls, app_root: Path, fieldday_name: str) -> bool:
        """Return True if the field day folder + metadata file exist."""
        p = Path(app_root) / _FIELDDAYS_DIR / fieldday_name / _FILE_FIELDDAY
        return p.exists()

    def delete_all_data(self) -> None:
        """Remove all JSON files for this field day (keeps the folder).

        Used in tests only.  Does NOT remove the folder itself.
        """
        import shutil
        for fname in [
            _FILE_FIELDDAY,
            _FILE_STATIONS,
            _FILE_QSOS,
            _FILE_OVERRIDES,
            _FILE_SYNC_LOG,
        ]:
            p = self._path(fname)
            if p.exists():
                p.unlink()
        exports = self._root / _DIR_EXPORTS
        if exports.exists():
            shutil.rmtree(exports)
            ensure_dir(exports)
        log.debug("Deleted all data files for field day: %s", self._name)
