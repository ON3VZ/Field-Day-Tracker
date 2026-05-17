"""
app/app_controller.py
=====================
Central application coordinator for N1MM Field Day Tracker.

The controller owns all application state and exposes a clean API
that the UI can call.  It has **no Tkinter imports** and can be
fully tested without a display.

Responsibilities
----------------
- Load / save AppSettings
- Open, create, switch active field day
- Manage the station list (import CSV, add manual)
- Receive QSOs from the UDP listener and pass them to the sync engine
- Run full recalculate (manual sync)
- Maintain the current matrix in memory
- Start / stop the N1MM UDP listener
- Notify the UI via registered callbacks (Observer pattern)

Observer callbacks
------------------
register_on_matrix_changed(fn)   – called after any matrix update
register_on_status_changed(fn)   – called when UDP connection status changes
register_on_fieldday_changed(fn) – called when the active field day changes
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.core.models import (
    AppSettings, FieldDay, Override, ReceivedQSO,
    Station, StationBandStatus, SyncResult,
)
from app.core.status import Status
from app.core.callsign import normalize
from app.core.sync_engine import SyncContext, SyncEngine
from app.i18n.translations import set_language
from app.importers.csv_importer import CSVImporter, ImportResult
from app.integrations.n1mm_udp_listener import ListenerStatus, N1MMUDPListener
from app.storage.fieldday_repository import (
    AppSettingsRepository,
    FieldDayRepository,
    is_valid_fieldday_name,
)

log = logging.getLogger(__name__)


class AppController:
    """Orchestrates all application state and logic.

    Parameters
    ----------
    app_root:
        Root directory where ``app_settings.json`` and ``fielddays/``
        live.  Determined by :func:`app.main._resolve_app_root`.
    """

    def __init__(self, app_root: Path) -> None:
        self._app_root = Path(app_root)

        # Repositories
        self._settings_repo = AppSettingsRepository(self._app_root)
        self._settings: AppSettings = AppSettings()
        self._fd_repo: FieldDayRepository | None = None

        # Active field day state
        self._fieldday: FieldDay | None = None
        self._stations: list[Station] = []
        self._qsos: list[ReceivedQSO] = []
        self._overrides: dict[tuple[str, str], Override] = {}
        self._matrix: dict[tuple[str, str], StationBandStatus] = {}

        # UDP listener
        self._listener: N1MMUDPListener | None = None

        # Observer callbacks
        self._on_matrix_changed:   list[Callable] = []
        self._on_status_changed:   list[Callable] = []
        self._on_fieldday_changed: list[Callable] = []

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def startup(self) -> None:
        """Load settings, open last active field day, start UDP listener."""
        self._settings = self._settings_repo.load()
        set_language(self._settings.ui_language)
        log.info("AppController startup. Language: %s", self._settings.ui_language)

        # Restore last active field day
        last = self._settings.last_active_fieldday
        if last and FieldDayRepository.exists(self._app_root, last):
            self._open_fieldday_by_name(last)
        else:
            log.info("No last active field day to restore.")

        # Start UDP listener
        self._start_listener()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_csv(self, path: Path) -> "ExportResult":
        """Export the current matrix to a CSV file."""
        from app.exporters.csv_exporter import CSVExporter, ExportResult
        if not self._fieldday:
            return ExportResult(path=path, rows_written=0, success=False,
                                error="No active field day.")
        return CSVExporter.export(
            path, self._fieldday, self._stations, self._matrix
        )

    def export_pdf(self, path: Path) -> "ExportResult":
        """Export a PDF report of the current field day."""
        from app.exporters.pdf_exporter import PDFExporter, ExportResult
        if not self._fieldday:
            return ExportResult(path=path, success=False,
                                error="No active field day.")
        return PDFExporter.export(
            path, self._fieldday, self._stations,
            self._matrix, self._settings
        )

    def publish_to_github_pages(self) -> "PublishResult":
        """Generate HTML and push to GitHub Pages via API."""
        from app.exporters.github_pages_publisher import GHPagesPublisher, PublishResult
        from app.security.token_store import TokenStore

        s = self._settings
        token = TokenStore.decrypt(s.github_token_encrypted)
        if not token:
            return PublishResult(success=False,
                                 message="GitHub token not set or could not be decrypted.")
        if not s.github_repo:
            return PublishResult(success=False, message="GitHub repository not configured.")
        if not self._fieldday:
            return PublishResult(success=False, message="No active field day.")

        result = GHPagesPublisher.publish(
            token=token,
            repo=s.github_repo,
            fieldday=self._fieldday,
            stations=self._stations,
            matrix=self._matrix,
            settings=s,
            refresh_seconds=s.github_page_refresh_seconds,
        )
        if result.success:
            s.github_last_published_utc = result.timestamp_utc
            if result.url:
                s.github_pages_url = result.url
            self._save_settings()
        return result

    def get_export_folder(self) -> Path:
        """Return the configured export folder, creating it if needed."""
        from app.storage.json_store import ensure_dir
        folder = self._settings.export_folder or "exports"
        p = Path(folder)
        if not p.is_absolute():
            p = self._app_root / p
        if self._fieldday:
            p = p / self._fieldday.name
        ensure_dir(p)
        return p

    def shutdown(self) -> None:
        """Stop listener and persist any pending state."""
        if self._listener:
            self._listener.stop()
        self._save_settings()
        log.info("AppController shutdown complete.")

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def update_settings(self, new_settings: AppSettings) -> None:
        """Apply and persist updated settings."""
        lang_changed = new_settings.ui_language != self._settings.ui_language
        udp_changed = (
            new_settings.n1mm_udp_host != self._settings.n1mm_udp_host
            or new_settings.n1mm_udp_port != self._settings.n1mm_udp_port
            or new_settings.freshness_threshold_seconds
               != self._settings.freshness_threshold_seconds
        )
        strict_changed = (
            new_settings.strict_callsign_matching
            != self._settings.strict_callsign_matching
        )
        self._settings = new_settings
        self._save_settings()

        if lang_changed:
            set_language(self._settings.ui_language)

        if udp_changed and self._listener:
            self._start_listener()  # restarts with new settings

        if strict_changed and self._fieldday:
            self.recalculate()

        log.info("Settings updated.")

    def _save_settings(self) -> None:
        try:
            self._settings_repo.save(self._settings)
        except Exception as exc:  # noqa: BLE001
            log.error("Could not save settings: %s", exc)

    # ------------------------------------------------------------------
    # Field day management
    # ------------------------------------------------------------------

    @property
    def fieldday(self) -> FieldDay | None:
        return self._fieldday

    @property
    def has_active_fieldday(self) -> bool:
        return self._fieldday is not None

    def list_fielddays(self) -> list[str]:
        """Return sorted list of field day names on disk."""
        return FieldDayRepository.list_fielddays(self._app_root)

    def create_fieldday(self, fieldday: FieldDay) -> None:
        """Create a new field day and make it active.

        Parameters
        ----------
        fieldday:
            Fully populated FieldDay (name must be valid).

        Raises
        ------
        ValueError
            If the name is invalid or already exists.
        """
        if not is_valid_fieldday_name(fieldday.name):
            raise ValueError(
                f"Invalid field day name: {fieldday.name!r}"
            )
        if FieldDayRepository.exists(self._app_root, fieldday.name):
            raise ValueError(
                f"A field day named '{fieldday.name}' already exists."
            )

        repo = FieldDayRepository(self._app_root, fieldday.name)
        repo.save_fieldday(fieldday)
        log.info("Created field day: %s", fieldday.name)
        self._activate_fieldday(repo, fieldday)

    def open_fieldday(self, name: str) -> bool:
        """Open an existing field day by name.

        Returns True on success, False if not found.
        """
        if not FieldDayRepository.exists(self._app_root, name):
            log.warning("Field day not found: %s", name)
            return False
        repo = FieldDayRepository(self._app_root, name)
        fd = repo.load_fieldday()
        self._activate_fieldday(repo, fd)
        return True

    def update_fieldday(self, fieldday: FieldDay) -> None:
        """Save changes to the active field day and recalculate."""
        if self._fd_repo is None:
            raise RuntimeError("No active field day.")
        self._fd_repo.save_fieldday(fieldday)
        self._fieldday = fieldday
        self.recalculate()
        self._notify_fieldday_changed()

    def _open_fieldday_by_name(self, name: str) -> None:
        repo = FieldDayRepository(self._app_root, name)
        fd = repo.load_fieldday()
        self._activate_fieldday(repo, fd)

    def _activate_fieldday(
        self,
        repo: FieldDayRepository,
        fd: FieldDay,
    ) -> None:
        """Make *fd* the active field day, load its data and recalculate."""
        self._fd_repo = repo
        self._fieldday = fd
        self._stations  = repo.load_stations()
        self._qsos      = repo.load_qsos()
        self._overrides = repo.load_overrides()
        self._matrix    = {}

        # Persist last active
        self._settings.last_active_fieldday = fd.name
        self._save_settings()

        log.info(
            "Activated field day: %s (%d stations, %d QSOs, %d overrides)",
            fd.name, len(self._stations), len(self._qsos), len(self._overrides),
        )
        self.recalculate()
        self._notify_fieldday_changed()

    # ------------------------------------------------------------------
    # Station management
    # ------------------------------------------------------------------

    @property
    def stations(self) -> list[Station]:
        return list(self._stations)

    def import_csv(self, path: Path) -> ImportResult:
        """Import stations from a CSV file.

        Merges with existing stations according to re-import rules.
        Does NOT auto-remove missing stations — caller handles that.
        """
        result = CSVImporter.import_csv(
            path,
            existing_stations=self._stations,
            strict=self._settings.strict_callsign_matching,
            column_mapping=self._settings.csv_column_mapping,
        )
        if result.success and self._fd_repo:
            self._stations = result.stations
            self._fd_repo.save_stations(self._stations)
            self.recalculate()
        return result

    def apply_csv_removals(self, callsigns_to_remove: list[str]) -> None:
        """Remove stations confirmed by the user after a CSV re-import."""
        self._stations = CSVImporter.apply_removals(
            self._stations, callsigns_to_remove
        )
        if self._fd_repo:
            self._fd_repo.save_stations(self._stations)
        self.recalculate()

    def add_station_manual(self, station: Station) -> bool:
        """Add a station manually.  Returns False if already exists."""
        norm = normalize(
            station.callsign,
            strict=self._settings.strict_callsign_matching,
        )
        station.normalized_callsign = norm
        station.source = "manual"

        existing = {s.normalized_callsign for s in self._stations}
        if norm in existing:
            log.debug("Manual add: %s already exists.", norm)
            return False

        self._stations.append(station)
        if self._fd_repo:
            self._fd_repo.save_stations(self._stations)
        self.recalculate()
        return True

    def update_station_remarks(
        self, normalized_callsign: str, remarks: str
    ) -> None:
        """Update the remarks for a station and persist."""
        for s in self._stations:
            if s.normalized_callsign == normalized_callsign:
                s.remarks = remarks
                break
        if self._fd_repo:
            self._fd_repo.save_stations(self._stations)

    # ------------------------------------------------------------------
    # Manual overrides
    # ------------------------------------------------------------------

    def set_override(
        self,
        normalized_callsign: str,
        band: str,
        status: Status,
    ) -> None:
        """Set a manual override for callsign+band and recalculate."""
        o = Override(
            normalized_callsign=normalized_callsign,
            band=band,
            status=status.value,
        )
        self._overrides = self._fd_repo.set_override(self._overrides, o)
        self._fd_repo.save_overrides(self._overrides)
        self.recalculate()

    def clear_override(self, normalized_callsign: str, band: str) -> None:
        """Remove override for callsign+band and recalculate."""
        self._overrides = self._fd_repo.clear_override(
            self._overrides, normalized_callsign, band
        )
        self._fd_repo.save_overrides(self._overrides)
        self.recalculate()

    # ------------------------------------------------------------------
    # Sync / recalculate
    # ------------------------------------------------------------------

    @property
    def matrix(self) -> dict[tuple[str, str], StationBandStatus]:
        return dict(self._matrix)

    def recalculate(self) -> SyncResult:
        """Re-compute the full matrix from stored data.

        Called after any data change (CSV import, override, settings).
        """
        if not self._fieldday:
            return SyncResult()

        ctx = self._build_context()
        self._matrix, result = SyncEngine.recalculate(ctx)

        # Persist sync timestamp
        self._fieldday.last_sync_utc = datetime.now(timezone.utc).isoformat()
        if self._fd_repo:
            self._fd_repo.save_fieldday(self._fieldday)
            self._fd_repo.append_sync_log({
                "type": "recalculate",
                "worked": result.worked_combinations,
                "unworked": result.unworked_combinations,
                "excluded": result.excluded_count,
                "overrides": result.manual_override_count,
                "errors": result.errors,
            })

        log.info(
            "Recalculate complete: %d worked, %d unworked",
            result.worked_combinations, result.unworked_combinations,
        )
        self._notify_matrix_changed()
        return result

    def get_station_statistics(self) -> dict[str, int]:
        """Return fully/partially/not-worked station counts."""
        if not self._fieldday:
            return {"fully_worked": 0, "partially_worked": 0, "not_worked": 0}
        return SyncEngine.compute_station_statistics(
            self._matrix,
            self._stations,
            self._fieldday.selected_bands,
        )

    def get_summary(self) -> dict:
        """Return a summary dict for the status bar / export."""
        fd = self._fieldday
        if fd is None:
            return {}
        matrix = self._matrix
        bands = set(fd.selected_bands)
        station_norms = {s.normalized_callsign for s in self._stations}

        worked = unworked = excluded = overrides = 0
        for (nc, band), cell in matrix.items():
            if band not in bands or nc not in station_norms:
                continue
            if cell.status.is_excluded():
                excluded += 1
            elif cell.status.is_worked():
                worked += 1
            else:
                unworked += 1
            if cell.has_override:
                overrides += 1

        station_stats = self.get_station_statistics()
        return {
            "total_stations": len(self._stations),
            "total_bands": len(bands),
            "total_combinations": len(self._stations) * len(bands),
            "worked": worked,
            "unworked": unworked,
            "excluded": excluded,
            "overrides": overrides,
            **station_stats,
        }

    # ------------------------------------------------------------------
    # UDP listener
    # ------------------------------------------------------------------

    def _build_context(self) -> SyncContext:
        return SyncContext(
            fieldday=self._fieldday,
            stations=self._stations,
            qsos=self._qsos,
            overrides=self._overrides,
            strict=self._settings.strict_callsign_matching,
        )

    def _start_listener(self) -> None:
        """(Re)start the UDP listener with current settings."""
        if self._listener:
            self._listener.stop()

        # Resolve effective host/port: field day overrides global if set
        host = self._settings.n1mm_udp_host
        port = self._settings.n1mm_udp_port
        if self._fieldday:
            if self._fieldday.n1mm_udp_host:
                host = self._fieldday.n1mm_udp_host
            if self._fieldday.n1mm_udp_port:
                port = self._fieldday.n1mm_udp_port

        threshold = self._settings.freshness_threshold_seconds
        if self._fieldday and self._fieldday.freshness_threshold_seconds:
            threshold = self._fieldday.freshness_threshold_seconds

        self._listener = N1MMUDPListener(
            host=host,
            port=port,
            on_qso_received=self._on_qso_received,
            on_status_change=self._on_listener_status,
            freshness_threshold=threshold,
            strict=self._settings.strict_callsign_matching,
        )
        self._listener.start()

    def _on_qso_received(self, qso: ReceivedQSO) -> None:
        """Called by UDP listener thread when a valid QSO arrives."""
        if self._fieldday is None or self._fd_repo is None:
            return

        # Store the QSO
        self._qsos = self._fd_repo.append_qso(qso, self._qsos)
        self._fd_repo.save_qsos(self._qsos)

        # Real-time matrix update (no full recalculate needed)
        ctx = self._build_context()
        self._matrix, changed = SyncEngine.process_single_qso(
            qso, ctx, self._matrix
        )

        if changed:
            self._notify_matrix_changed()

    def _on_listener_status(
        self, status: ListenerStatus, message: str
    ) -> None:
        """Called by UDP listener thread on status change."""
        self._notify_status_changed(status, message)

    @property
    def listener_status(self) -> ListenerStatus | None:
        if self._listener is None:
            return None
        return self._listener.status

    @property
    def listener_last_received_str(self) -> str:
        if self._listener is None:
            return "Never"
        return self._listener.last_received_str

    # ------------------------------------------------------------------
    # Observer registration
    # ------------------------------------------------------------------

    def register_on_matrix_changed(self, fn: Callable) -> None:
        self._on_matrix_changed.append(fn)

    def register_on_status_changed(self, fn: Callable) -> None:
        self._on_status_changed.append(fn)

    def register_on_fieldday_changed(self, fn: Callable) -> None:
        self._on_fieldday_changed.append(fn)

    def _notify_matrix_changed(self) -> None:
        for fn in self._on_matrix_changed:
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                log.error("matrix_changed callback error: %s", exc)

    def _notify_status_changed(
        self, status: ListenerStatus, message: str
    ) -> None:
        for fn in self._on_status_changed:
            try:
                fn(status, message)
            except Exception as exc:  # noqa: BLE001
                log.error("status_changed callback error: %s", exc)

    def _notify_fieldday_changed(self) -> None:
        for fn in self._on_fieldday_changed:
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                log.error("fieldday_changed callback error: %s", exc)
