"""
app/core/models.py
==================
Core data models for N1MM Field Day Tracker.

All timestamps are stored and compared in **UTC**.
Serialisation to/from JSON dicts is handled here so the storage layer
stays generic.

Models
------
AppSettings     – global application settings (language, UDP, colours, …)
FieldDay        – a field day event with start/end period
Station         – a participating station (from CSV or manually added)
ReceivedQSO     – a QSO received from N1MM via UDP
Override        – a manual status override for a callsign+band pair
StationBandStatus – computed view of one station×band cell (not persisted)
SyncResult      – result of a sync/recalculate operation (not persisted)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.core.status import Status, DEFAULT_STATUS_COLORS
from app.core.band_plan import DEFAULT_SELECTED_BANDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string to an aware datetime in UTC.

    Returns None if *value* is None or cannot be parsed.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# AppSettings
# ---------------------------------------------------------------------------

@dataclass
class AppSettings:
    """Global application settings stored in ``app_settings.json``.

    Attributes
    ----------
    ui_language:
        Active UI language code (``"en"``, ``"nl"``, ``"fr"``, ``"es"``).
    n1mm_udp_host:
        Host address the UDP listener binds to.
    n1mm_udp_port:
        UDP port number.
    freshness_threshold_seconds:
        Seconds since last N1MM message before connection is shown as stale.
    auto_sync_enabled:
        Whether the UI refreshes automatically on each received QSO.
    strict_callsign_matching:
        When True, callsigns must match exactly.
        When False, /P /M /QRP etc. are stripped before matching.
    default_selected_bands:
        Bands pre-selected when creating a new field day.
    status_colors:
        Dict mapping status value strings to hex colour strings.
    export_folder:
        Default folder path for CSV/PDF exports.
    last_active_fieldday:
        Name of the last active field day (subfolder name under fielddays/).
    """

    ui_language: str = "en"
    n1mm_udp_host: str = "127.0.0.1"
    n1mm_udp_port: int = 12060
    freshness_threshold_seconds: int = 30
    auto_sync_enabled: bool = True
    strict_callsign_matching: bool = False
    default_selected_bands: list[str] = field(
        default_factory=lambda: list(DEFAULT_SELECTED_BANDS)
    )
    status_colors: dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_STATUS_COLORS)
    )
    export_folder: str = "exports"
    last_active_fieldday: Optional[str] = None
    csv_column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "callsign": "callsign",
            "name":     "name",
            "club":     "club",
            "remarks":  "remarks",
        }
    )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "ui_language": self.ui_language,
            "n1mm_udp_host": self.n1mm_udp_host,
            "n1mm_udp_port": self.n1mm_udp_port,
            "freshness_threshold_seconds": self.freshness_threshold_seconds,
            "auto_sync_enabled": self.auto_sync_enabled,
            "strict_callsign_matching": self.strict_callsign_matching,
            "default_selected_bands": self.default_selected_bands,
            "status_colors": self.status_colors,
            "export_folder": self.export_folder,
            "last_active_fieldday": self.last_active_fieldday,
            "csv_column_mapping": self.csv_column_mapping,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        s = cls()
        s.ui_language = data.get("ui_language", s.ui_language)
        s.n1mm_udp_host = data.get("n1mm_udp_host", s.n1mm_udp_host)
        s.n1mm_udp_port = int(data.get("n1mm_udp_port", s.n1mm_udp_port))
        s.freshness_threshold_seconds = int(
            data.get("freshness_threshold_seconds", s.freshness_threshold_seconds)
        )
        s.auto_sync_enabled = bool(data.get("auto_sync_enabled", s.auto_sync_enabled))
        s.strict_callsign_matching = bool(
            data.get("strict_callsign_matching", s.strict_callsign_matching)
        )
        s.default_selected_bands = data.get(
            "default_selected_bands", s.default_selected_bands
        )
        s.status_colors = data.get("status_colors", s.status_colors)
        s.export_folder = data.get("export_folder", s.export_folder)
        s.last_active_fieldday = data.get("last_active_fieldday")
        if "csv_column_mapping" in data and isinstance(data["csv_column_mapping"], dict):
            # Merge: keep defaults for any key not in saved mapping
            for k, v in data["csv_column_mapping"].items():
                if isinstance(k, str) and isinstance(v, str):
                    s.csv_column_mapping[k] = v
        return s


# ---------------------------------------------------------------------------
# FieldDay
# ---------------------------------------------------------------------------

@dataclass
class FieldDay:
    """A field day event.

    The event spans the period [start_utc, end_utc].  Only QSOs whose
    timestamp falls within this window are counted.

    Attributes
    ----------
    name:
        Unique identifier / folder name.  Allowed characters: letters,
        digits, underscore, hyphen.
    location:
        Free-text location description.
    event_callsign:
        The callsign used on air during this event.
    organizer:
        Organizer name or club.
    start_utc:
        Start of the field day period (UTC, ISO-8601 string).
    end_utc:
        End of the field day period (UTC, ISO-8601 string).
    display_timezone:
        IANA timezone name used for displaying times in the UI,
        e.g. ``"Europe/Brussels"``.
    selected_bands:
        List of band names active for this field day, e.g. ``["160m","80m"]``.
    n1mm_udp_host:
        Per-field-day UDP host override (falls back to AppSettings if empty).
    n1mm_udp_port:
        Per-field-day UDP port override (0 = use AppSettings value).
    freshness_threshold_seconds:
        Per-field-day freshness threshold (0 = use AppSettings value).
    ui_language:
        Per-field-day language override (empty = use AppSettings value).
    strict_callsign_matching:
        Per-field-day strict matching override.
    remarks:
        Free-text remarks about this field day.
    operator_notes:
        Operator notes / operating plan.
    last_sync_utc:
        Timestamp of the last successful sync (UTC ISO-8601).
    created_at:
        Creation timestamp (UTC ISO-8601).
    updated_at:
        Last modification timestamp (UTC ISO-8601).
    """

    name: str = ""
    location: str = ""
    event_callsign: str = ""
    organizer: str = ""
    start_utc: str = ""
    end_utc: str = ""
    display_timezone: str = "UTC"
    selected_bands: list[str] = field(
        default_factory=lambda: list(DEFAULT_SELECTED_BANDS)
    )
    n1mm_udp_host: str = ""
    n1mm_udp_port: int = 0
    freshness_threshold_seconds: int = 0
    ui_language: str = ""
    strict_callsign_matching: bool = False
    remarks: str = ""
    operator_notes: str = ""
    last_sync_utc: Optional[str] = None
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def start_dt(self) -> datetime | None:
        """Parsed start time as an aware UTC datetime."""
        return _parse_dt(self.start_utc)

    @property
    def end_dt(self) -> datetime | None:
        """Parsed end time as an aware UTC datetime."""
        return _parse_dt(self.end_utc)

    def is_valid_period(self) -> bool:
        """Return True if end_utc is strictly after start_utc."""
        s, e = self.start_dt, self.end_dt
        if s is None or e is None:
            return False
        return e > s

    def qso_in_period(self, qso_timestamp_utc: str) -> bool:
        """Return True if *qso_timestamp_utc* falls within [start, end].

        Parameters
        ----------
        qso_timestamp_utc:
            ISO-8601 UTC timestamp string of the QSO.
        """
        qso_dt = _parse_dt(qso_timestamp_utc)
        s, e = self.start_dt, self.end_dt
        if qso_dt is None or s is None or e is None:
            return False
        return s <= qso_dt <= e

    def touch(self) -> None:
        """Update ``updated_at`` to the current UTC time."""
        self.updated_at = _utcnow()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "location": self.location,
            "event_callsign": self.event_callsign,
            "organizer": self.organizer,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "display_timezone": self.display_timezone,
            "selected_bands": self.selected_bands,
            "n1mm_udp_host": self.n1mm_udp_host,
            "n1mm_udp_port": self.n1mm_udp_port,
            "freshness_threshold_seconds": self.freshness_threshold_seconds,
            "ui_language": self.ui_language,
            "strict_callsign_matching": self.strict_callsign_matching,
            "remarks": self.remarks,
            "operator_notes": self.operator_notes,
            "last_sync_utc": self.last_sync_utc,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FieldDay":
        fd = cls()
        fd.name = data.get("name", "")
        fd.location = data.get("location", "")
        fd.event_callsign = data.get("event_callsign", "")
        fd.organizer = data.get("organizer", "")
        fd.start_utc = data.get("start_utc", "")
        fd.end_utc = data.get("end_utc", "")
        fd.display_timezone = data.get("display_timezone", "UTC")
        fd.selected_bands = data.get("selected_bands", list(DEFAULT_SELECTED_BANDS))
        fd.n1mm_udp_host = data.get("n1mm_udp_host", "")
        fd.n1mm_udp_port = int(data.get("n1mm_udp_port", 0))
        fd.freshness_threshold_seconds = int(
            data.get("freshness_threshold_seconds", 0)
        )
        fd.ui_language = data.get("ui_language", "")
        fd.strict_callsign_matching = bool(
            data.get("strict_callsign_matching", False)
        )
        fd.remarks = data.get("remarks", "")
        fd.operator_notes = data.get("operator_notes", "")
        fd.last_sync_utc = data.get("last_sync_utc")
        fd.created_at = data.get("created_at", _utcnow())
        fd.updated_at = data.get("updated_at", _utcnow())
        return fd


# ---------------------------------------------------------------------------
# Station
# ---------------------------------------------------------------------------

@dataclass
class Station:
    """A participating station imported from CSV or added manually.

    Attributes
    ----------
    callsign:
        Original callsign as entered (may include /P etc.).
    normalized_callsign:
        Normalised form used for matching (depends on strict setting
        at import time — stored so it can be re-derived if needed).
    name:
        Optional operator name.
    club:
        Optional club abbreviation.
    remarks:
        Free-text remarks visible in the matrix.
    source:
        ``"csv"`` or ``"manual"``.
    added_at:
        UTC ISO-8601 timestamp when this station was added.
    """

    callsign: str = ""
    normalized_callsign: str = ""
    name: str = ""
    club: str = ""
    remarks: str = ""
    source: str = "csv"          # "csv" | "manual"
    added_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "callsign": self.callsign,
            "normalized_callsign": self.normalized_callsign,
            "name": self.name,
            "club": self.club,
            "remarks": self.remarks,
            "source": self.source,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Station":
        s = cls()
        s.callsign = data.get("callsign", "")
        s.normalized_callsign = data.get("normalized_callsign", s.callsign.upper())
        s.name = data.get("name", "")
        s.club = data.get("club", "")
        s.remarks = data.get("remarks", "")
        s.source = data.get("source", "csv")
        s.added_at = data.get("added_at", _utcnow())
        return s


# ---------------------------------------------------------------------------
# ReceivedQSO
# ---------------------------------------------------------------------------

@dataclass
class ReceivedQSO:
    """A QSO contact received from N1MM Logger+ via UDP broadcast.

    Attributes
    ----------
    original_callsign:
        Raw callsign from N1MM (``<call>`` element).
    normalized_callsign:
        Normalised form (computed at receive time with current strict setting).
    band:
        Band name (e.g. ``"40m"``), derived from N1MM band field or frequency.
    frequency_hz:
        Frequency in Hz (raw value * 10 from N1MM's 10-Hz units), or None.
    mode:
        Operating mode (e.g. ``"CW"``, ``"SSB"``), or empty string.
    timestamp_utc:
        QSO timestamp in UTC (ISO-8601).
    source:
        Always ``"n1mm_udp"`` for received QSOs.
    raw_message:
        The original UDP XML payload (stored for debugging/re-processing).
    received_at:
        Wall-clock time when this app received the UDP packet (UTC ISO-8601).
    n1mm_id:
        The ``<ID>`` field from N1MM, used to detect duplicate broadcasts.
    contest_name:
        The ``<contestname>`` field from N1MM.
    """

    original_callsign: str = ""
    normalized_callsign: str = ""
    band: str = ""
    frequency_hz: Optional[float] = None
    mode: str = ""
    timestamp_utc: str = ""
    source: str = "n1mm_udp"
    raw_message: str = ""
    received_at: str = field(default_factory=_utcnow)
    n1mm_id: str = ""
    contest_name: str = ""

    def to_dict(self) -> dict:
        return {
            "original_callsign": self.original_callsign,
            "normalized_callsign": self.normalized_callsign,
            "band": self.band,
            "frequency_hz": self.frequency_hz,
            "mode": self.mode,
            "timestamp_utc": self.timestamp_utc,
            "source": self.source,
            "raw_message": self.raw_message,
            "received_at": self.received_at,
            "n1mm_id": self.n1mm_id,
            "contest_name": self.contest_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReceivedQSO":
        q = cls()
        q.original_callsign = data.get("original_callsign", "")
        q.normalized_callsign = data.get("normalized_callsign", "")
        q.band = data.get("band", "")
        q.frequency_hz = data.get("frequency_hz")
        q.mode = data.get("mode", "")
        q.timestamp_utc = data.get("timestamp_utc", "")
        q.source = data.get("source", "n1mm_udp")
        q.raw_message = data.get("raw_message", "")
        q.received_at = data.get("received_at", _utcnow())
        q.n1mm_id = data.get("n1mm_id", "")
        q.contest_name = data.get("contest_name", "")
        return q


# ---------------------------------------------------------------------------
# Override
# ---------------------------------------------------------------------------

@dataclass
class Override:
    """A manual status override for a specific callsign+band combination.

    The key for an override is ``(normalized_callsign, band)``.
    Manual overrides always take priority over N1MM data.

    Attributes
    ----------
    normalized_callsign:
        The normalised callsign this override applies to.
    band:
        Band name (e.g. ``"40m"``).
    status:
        The manually assigned status value string.
    set_at:
        UTC ISO-8601 timestamp when this override was set.
    set_by:
        Free-text label for who set the override (optional).
    note:
        Optional free-text note explaining the override.
    """

    normalized_callsign: str = ""
    band: str = ""
    status: str = Status.MANUAL_WORKED.value
    set_at: str = field(default_factory=_utcnow)
    set_by: str = ""
    note: str = ""

    @property
    def key(self) -> tuple[str, str]:
        """Unique key: (normalized_callsign, band)."""
        return (self.normalized_callsign, self.band)

    def to_dict(self) -> dict:
        return {
            "normalized_callsign": self.normalized_callsign,
            "band": self.band,
            "status": self.status,
            "set_at": self.set_at,
            "set_by": self.set_by,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Override":
        o = cls()
        o.normalized_callsign = data.get("normalized_callsign", "")
        o.band = data.get("band", "")
        o.status = data.get("status", Status.MANUAL_WORKED.value)
        o.set_at = data.get("set_at", _utcnow())
        o.set_by = data.get("set_by", "")
        o.note = data.get("note", "")
        return o


# ---------------------------------------------------------------------------
# StationBandStatus  (computed, not persisted)
# ---------------------------------------------------------------------------

@dataclass
class StationBandStatus:
    """Computed status for one station × band cell in the matrix.

    This is the *result* of the sync engine — not stored to disk.

    Attributes
    ----------
    normalized_callsign:
        Station identifier.
    band:
        Band name.
    status:
        Effective status after applying overrides.
    has_override:
        True if a manual override is active.
    worked_timestamp_utc:
        Timestamp of the first/most-recent N1MM QSO, or None.
    mode:
        Mode of the worked QSO, or empty.
    frequency_hz:
        Frequency in Hz, or None.
    """

    normalized_callsign: str = ""
    band: str = ""
    status: Status = Status.NOT_WORKED
    has_override: bool = False
    worked_timestamp_utc: Optional[str] = None
    mode: str = ""
    frequency_hz: Optional[float] = None


# ---------------------------------------------------------------------------
# SyncResult  (not persisted)
# ---------------------------------------------------------------------------

@dataclass
class SyncResult:
    """Summary returned by the sync engine after a recalculate run.

    Attributes
    ----------
    total_qsos_processed:
        Number of stored QSOs that were evaluated.
    qsos_in_period:
        Number of QSOs whose timestamp fell within the field day period.
    qsos_ignored_unknown:
        QSOs discarded because the callsign is not in the station list.
    qsos_ignored_out_of_period:
        QSOs discarded because their timestamp is outside the field day window.
    worked_combinations:
        Number of callsign+band pairs now showing as worked.
    unworked_combinations:
        Number of callsign+band pairs still unworked.
    manual_override_count:
        Total number of active manual overrides.
    excluded_count:
        Number of callsign+band pairs that are excluded.
    errors:
        List of non-fatal error messages encountered during sync.
    """

    total_qsos_processed: int = 0
    qsos_in_period: int = 0
    qsos_ignored_unknown: int = 0
    qsos_ignored_out_of_period: int = 0
    worked_combinations: int = 0
    unworked_combinations: int = 0
    manual_override_count: int = 0
    excluded_count: int = 0
    errors: list[str] = field(default_factory=list)
