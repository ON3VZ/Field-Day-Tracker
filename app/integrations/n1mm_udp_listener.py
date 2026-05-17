"""
app/integrations/n1mm_udp_listener.py
======================================
UDP listener for N1MM Logger+ Contact broadcasts.

Architecture
------------
The listener runs in a **daemon background thread** so it never blocks
the Tkinter main thread.  Communication back to the UI uses a simple
**callback / Observer pattern**: callers register a callback that is
invoked (on the listener thread) each time a valid QSO is received.

The callback is the only coupling between this module and the rest of
the application.  The UI layer is responsible for scheduling any
Tkinter widget updates on the main thread (via ``root.after(0, fn)``).

Thread safety
-------------
- ``_running`` flag is set/read atomically (bool assignment is GIL-safe).
- The socket's ``settimeout`` ensures the thread wakes regularly so it
  can check the ``_running`` flag even when no data arrives.
- Callback invocation happens on the listener thread; UI code must use
  ``root.after`` to marshal updates back to the Tkinter thread.

Usage
-----
::

    def on_qso(qso: ReceivedQSO) -> None:
        # called on listener thread — schedule UI update via root.after
        root.after(0, lambda: update_matrix(qso))

    listener = N1MMUDPListener(
        host="127.0.0.1",
        port=12060,
        on_qso_received=on_qso,
        on_status_change=lambda status, msg: print(status, msg),
    )
    listener.start()
    # ... later ...
    listener.stop()
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from app.integrations.n1mm_parser import N1MMParser
from app.core.models import ReceivedQSO

log = logging.getLogger(__name__)

# UDP receive buffer size (N1MM messages are typically < 2 KB)
_BUFFER_SIZE = 8192

# Socket timeout — how often the thread wakes to check _running
_SOCKET_TIMEOUT = 1.0  # seconds


class ListenerStatus(str, Enum):
    """Connection status values reported to the UI."""
    STARTING  = "starting"
    WAITING   = "waiting"    # listening, no data yet
    CONNECTED = "connected"  # data received within freshness threshold
    STALE     = "stale"      # no data for > freshness_threshold seconds
    ERROR     = "error"      # socket could not be opened
    STOPPED   = "stopped"


# Type aliases for callbacks
QSOCallback    = Callable[[ReceivedQSO], None]
StatusCallback = Callable[[ListenerStatus, str], None]


class N1MMUDPListener:
    """Background UDP listener for N1MM Logger+ contact broadcasts.

    Parameters
    ----------
    host:
        IP address to bind to (e.g. ``"127.0.0.1"`` or ``"0.0.0.0"``).
    port:
        UDP port to listen on (default ``12060``).
    on_qso_received:
        Callback invoked with each successfully parsed
        :class:`~app.core.models.ReceivedQSO`.  Called on the listener
        thread — schedule Tkinter updates via ``root.after``.
    on_status_change:
        Optional callback invoked when the connection status changes.
        Receives ``(ListenerStatus, human_readable_message)``.
    freshness_threshold:
        Seconds after the last received message before status becomes
        ``STALE`` (default ``30``).
    strict:
        Callsign normalisation mode forwarded to the parser.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 12060,
        on_qso_received: QSOCallback | None = None,
        on_status_change: StatusCallback | None = None,
        freshness_threshold: int = 30,
        strict: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._on_qso = on_qso_received
        self._on_status = on_status_change
        self._freshness = freshness_threshold
        self._strict = strict

        self._running = False
        self._thread: threading.Thread | None = None
        self._last_received: datetime | None = None
        self._status = ListenerStatus.STOPPED
        self._packets_received = 0
        self._qsos_parsed = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the listener thread.  No-op if already running."""
        if self._running:
            log.warning("UDP listener already running.")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name="N1MM-UDP-Listener",
            daemon=True,
        )
        self._thread.start()
        log.info("UDP listener starting on %s:%d", self._host, self._port)

    def stop(self) -> None:
        """Signal the listener thread to stop and wait for it to exit."""
        if not self._running:
            return
        log.info("Stopping UDP listener.")
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None
        self._set_status(ListenerStatus.STOPPED, "Listener stopped.")

    def restart(
        self,
        host: str | None = None,
        port: int | None = None,
        freshness_threshold: int | None = None,
        strict: bool | None = None,
    ) -> None:
        """Stop, update settings, and restart the listener."""
        self.stop()
        if host is not None:
            self._host = host
        if port is not None:
            self._port = port
        if freshness_threshold is not None:
            self._freshness = freshness_threshold
        if strict is not None:
            self._strict = strict
        self.start()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> ListenerStatus:
        return self._status

    @property
    def last_received(self) -> datetime | None:
        """UTC datetime of the last received N1MM packet, or None."""
        with self._lock:
            return self._last_received

    @property
    def last_received_str(self) -> str:
        """Human-readable last-received time, or 'Never'."""
        with self._lock:
            if self._last_received is None:
                return "Never"
            return self._last_received.strftime("%Y-%m-%d %H:%M:%S UTC")

    @property
    def packets_received(self) -> int:
        return self._packets_received

    @property
    def qsos_parsed(self) -> int:
        return self._qsos_parsed

    # ------------------------------------------------------------------
    # Internal — listener thread
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Main listener loop — runs in the background thread."""
        sock = self._open_socket()
        if sock is None:
            return  # Error already logged and status set

        self._set_status(ListenerStatus.WAITING, f"Listening on {self._host}:{self._port}…")
        last_freshness_check = time.monotonic()

        try:
            while self._running:
                # Receive a UDP packet (or timeout after _SOCKET_TIMEOUT)
                try:
                    data, addr = sock.recvfrom(_BUFFER_SIZE)
                except socket.timeout:
                    # No data — check freshness
                    self._check_freshness()
                    continue
                except OSError as exc:
                    if self._running:
                        log.error("UDP receive error: %s", exc)
                        self._set_status(
                            ListenerStatus.ERROR, f"Receive error: {exc}"
                        )
                    break

                self._packets_received += 1
                log.debug(
                    "UDP packet from %s:%d (%d bytes)", addr[0], addr[1], len(data)
                )

                # Quick pre-filter before full parse
                if not N1MMParser.is_contact_message(data):
                    log.debug("Non-contact UDP packet ignored.")
                    continue

                # Parse
                qso = self._safe_parse(data)
                if qso is None:
                    continue

                # Update last-received time and status
                with self._lock:
                    self._last_received = datetime.now(timezone.utc)
                self._qsos_parsed += 1
                self._set_status(
                    ListenerStatus.CONNECTED,
                    f"Last contact: {qso.original_callsign} on {qso.band}",
                )

                # Invoke callback
                if self._on_qso:
                    try:
                        self._on_qso(qso)
                    except Exception as exc:  # noqa: BLE001
                        log.error("QSO callback raised an exception: %s", exc)

                # Periodic freshness check (even when receiving data)
                now = time.monotonic()
                if now - last_freshness_check > self._freshness:
                    self._check_freshness()
                    last_freshness_check = now

        finally:
            try:
                sock.close()
            except OSError:
                pass
            log.info(
                "UDP listener stopped. Packets: %d, QSOs parsed: %d",
                self._packets_received, self._qsos_parsed,
            )

    def _open_socket(self) -> socket.socket | None:
        """Open and bind the UDP socket.  Returns None on failure."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(_SOCKET_TIMEOUT)
            sock.bind((self._host, self._port))
            log.info("UDP socket bound to %s:%d", self._host, self._port)
            return sock
        except OSError as exc:
            msg = f"Cannot open UDP socket on {self._host}:{self._port}: {exc}"
            log.error(msg)
            self._set_status(ListenerStatus.ERROR, msg)
            self._running = False
            return None

    def _safe_parse(self, data: bytes) -> ReceivedQSO | None:
        """Parse a UDP packet, swallowing all exceptions."""
        try:
            return N1MMParser.parse(data, strict=self._strict)
        except Exception as exc:  # noqa: BLE001
            log.warning("Unexpected parser error: %s", exc)
            return None

    def _check_freshness(self) -> None:
        """Update status to STALE if no data has arrived recently."""
        with self._lock:
            last = self._last_received

        if last is None:
            # Never received anything — stay WAITING
            if self._status != ListenerStatus.WAITING:
                self._set_status(
                    ListenerStatus.WAITING,
                    f"Listening on {self._host}:{self._port}…",
                )
            return

        age = (datetime.now(timezone.utc) - last).total_seconds()
        if age > self._freshness:
            if self._status != ListenerStatus.STALE:
                self._set_status(
                    ListenerStatus.STALE,
                    f"No data for {int(age)}s (threshold: {self._freshness}s)",
                )
        else:
            if self._status == ListenerStatus.STALE:
                # Recovered
                self._set_status(ListenerStatus.CONNECTED, "Receiving data.")

    def _set_status(self, status: ListenerStatus, message: str) -> None:
        """Update internal status and invoke the status callback."""
        if self._status == status and status != ListenerStatus.CONNECTED:
            return  # avoid redundant callbacks
        self._status = status
        log.debug("Listener status: %s — %s", status.value, message)
        if self._on_status:
            try:
                self._on_status(status, message)
            except Exception as exc:  # noqa: BLE001
                log.error("Status callback raised an exception: %s", exc)
