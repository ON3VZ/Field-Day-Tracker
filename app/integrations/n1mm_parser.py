"""
app/integrations/n1mm_parser.py
================================
Parser for N1MM Logger+ UDP broadcast messages.

N1MM Logger+ sends XML messages over UDP when contacts are logged.
This module parses the ``<contactinfo>`` XML payload and converts it
to a :class:`~app.core.models.ReceivedQSO`.

N1MM Contact XML format (relevant fields)
------------------------------------------
::

    <contactinfo>
        <app>N1MM</app>
        <contestname>FDREG1</contestname>
        <ID>1234567890</ID>
        <timestamp>2025-06-21 10:30:00</timestamp>
        <call>ON3VZ</call>
        <band>40M</band>
        <rxfreq>703000</rxfreq>          <!-- frequency in 10-Hz units -->
        <txfreq>703000</txfreq>
        <mode>CW</mode>
        <operator>ON3VZ</operator>
        <mycall>ON0TEST</mycall>
        <IsRunQSO>1</IsRunQSO>
        <StationName>Radio1</StationName>
        ...
    </contactinfo>

Frequency encoding
------------------
N1MM encodes frequencies in units of **10 Hz**.
So ``rxfreq = 703000`` means 7 030 000 Hz = 7.030 MHz.

Timestamp format
----------------
N1MM sends ``<timestamp>`` as ``YYYY-MM-DD HH:MM:SS`` in UTC.

Public API
----------
N1MMParser.parse(raw_xml)  → ReceivedQSO | None
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from app.core.band_plan import band_from_n1mm_freq_field, band_from_n1mm_name
from app.core.callsign import normalize
from app.core.models import ReceivedQSO

log = logging.getLogger(__name__)

# N1MM timestamp format in the XML
_N1MM_TS_FORMAT = "%Y-%m-%d %H:%M:%S"

# The root element name for contact broadcasts
_CONTACT_ROOT = "contactinfo"


class N1MMParser:
    """Stateless parser for N1MM Logger+ Contact broadcast XML."""

    @staticmethod
    def parse(
        raw: str | bytes,
        *,
        strict: bool = False,
    ) -> ReceivedQSO | None:
        """Parse a raw N1MM UDP packet into a :class:`ReceivedQSO`.

        Parameters
        ----------
        raw:
            Raw XML string or bytes received from the UDP socket.
        strict:
            Callsign normalisation mode passed to
            :func:`~app.core.callsign.normalize`.

        Returns
        -------
        ReceivedQSO or None
            ``None`` if the message is not a contact broadcast, is
            malformed, or is missing critical fields (callsign or
            timestamp).  All errors are logged but never raised.
        """
        # Decode bytes if needed
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8", errors="replace")
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not decode UDP packet: %s", exc)
                return None

        raw = raw.strip()
        if not raw:
            return None

        # Parse XML
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            log.debug("XML parse error (not a contact message?): %s", exc)
            return None

        # Only handle <contactinfo> messages
        if root.tag.lower() != _CONTACT_ROOT:
            log.debug("Ignoring non-contact broadcast: <%s>", root.tag)
            return None

        def _get(tag: str) -> str:
            """Return text of first matching child element, or ''."""
            el = root.find(tag)
            if el is None:
                # Try case-insensitive search
                for child in root:
                    if child.tag.lower() == tag.lower():
                        return (child.text or "").strip()
                return ""
            return (el.text or "").strip()

        # --- Extract fields ---
        original_call = _get("call")
        if not original_call:
            log.debug("Contact message has no <call> field — skipped.")
            return None

        raw_timestamp = _get("timestamp")
        timestamp_utc = _parse_timestamp(raw_timestamp)
        if not timestamp_utc:
            log.debug(
                "Contact message has unparseable timestamp %r — skipped.",
                raw_timestamp,
            )
            return None

        # Band: try <band> first, then derive from <rxfreq>
        band_str = _get("band")
        rxfreq_str = _get("rxfreq") or _get("txfreq")

        frequency_hz: float | None = None
        if rxfreq_str:
            try:
                frequency_hz = float(rxfreq_str) * 10.0  # N1MM unit = 10 Hz
            except ValueError:
                pass

        # Resolve band name
        band_name = ""
        if band_str:
            b = band_from_n1mm_name(band_str)
            if b:
                band_name = b.name
        if not band_name and frequency_hz is not None:
            from app.core.band_plan import band_from_frequency_hz
            b = band_from_frequency_hz(frequency_hz)
            if b:
                band_name = b.name

        mode = _get("mode").upper()
        n1mm_id = _get("ID") or _get("id")
        contest_name = _get("contestname")

        # Build QSO
        qso = ReceivedQSO(
            original_callsign=original_call,
            normalized_callsign=normalize(original_call, strict=strict),
            band=band_name,
            frequency_hz=frequency_hz,
            mode=mode,
            timestamp_utc=timestamp_utc,
            source="n1mm_udp",
            raw_message=raw,
            n1mm_id=n1mm_id,
            contest_name=contest_name,
        )

        log.debug(
            "Parsed QSO: call=%s  band=%s  mode=%s  ts=%s  id=%s",
            original_call, band_name, mode, timestamp_utc, n1mm_id,
        )
        return qso

    @staticmethod
    def is_contact_message(raw: str | bytes) -> bool:
        """Return True if *raw* looks like a N1MM contact broadcast.

        Faster than a full parse — used to filter irrelevant UDP packets.
        """
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return _CONTACT_ROOT in raw.lower()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_timestamp(raw: str) -> str | None:
    """Parse a N1MM timestamp string to UTC ISO-8601.

    N1MM format: ``YYYY-MM-DD HH:MM:SS`` (UTC)

    Returns
    -------
    str or None
        ISO-8601 UTC string, or None if unparseable.
    """
    if not raw:
        return None
    try:
        dt = datetime.strptime(raw, _N1MM_TS_FORMAT)
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        pass
    # Try ISO format as fallback (some N1MM versions may differ)
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None
