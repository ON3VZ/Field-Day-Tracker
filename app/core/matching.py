"""
app/core/matching.py
====================
QSO-to-station matching logic for N1MM Field Day Tracker.

Matching rules
--------------
A QSO matches a station when:

1. The QSO's normalised callsign matches the station's normalised callsign
   (using the configured strict/non-strict mode).
2. The QSO timestamp falls within the active field day period (checked
   separately by the sync engine).
3. The station exists in the imported/manually-added participant list
   (unknown callsigns are silently ignored).
4. The QSO band is in the field day's selected bands.

This module is purely about callsign and band resolution — it has no
knowledge of overrides, period filtering, or UI.

Public API
----------
find_station(normalized_qso_call, station_map, strict)  → Station | None
resolve_band(qso)                                        → str | None
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.callsign import normalize
from app.core.band_plan import band_from_n1mm_freq_field, band_from_n1mm_name

if TYPE_CHECKING:
    from app.core.models import ReceivedQSO, Station

log = logging.getLogger(__name__)


def find_station(
    normalized_qso_call: str,
    station_map: dict[str, "Station"],
    *,
    strict: bool = False,
) -> "Station | None":
    """Find a matching station for a normalised QSO callsign.

    The lookup first tries an exact match against normalised station
    callsigns.  If ``strict=False`` and no exact match is found, an
    additional soft-match pass is performed (both sides re-normalised).

    Parameters
    ----------
    normalized_qso_call:
        Callsign already normalised with the same *strict* setting.
    station_map:
        Dict keyed by ``normalized_callsign`` → :class:`~app.core.models.Station`.
    strict:
        Matching mode.

    Returns
    -------
    Station or None
    """
    # Fast path: exact normalised-key lookup
    station = station_map.get(normalized_qso_call)
    if station is not None:
        return station

    if strict:
        return None

    # Soft path: re-normalise both sides in case the station_map was built
    # with a different strict setting than the current one.
    for station_norm, station in station_map.items():
        # Re-normalise both to the non-strict form and compare
        if normalize(station_norm, strict=False) == normalize(normalized_qso_call, strict=False):
            log.debug(
                "Soft-matched %s → %s", normalized_qso_call, station_norm
            )
            return station

    return None


def resolve_band(qso: "ReceivedQSO") -> str | None:
    """Determine the band name for a QSO.

    Resolution order:
    1. ``qso.band`` if already set and valid.
    2. Derive from ``qso.frequency_hz`` (set by the N1MM parser).

    Parameters
    ----------
    qso:
        A :class:`~app.core.models.ReceivedQSO` instance.

    Returns
    -------
    str or None
        Band name (e.g. ``"40m"``) or ``None`` if unresolvable.
    """
    # 1. Band already set
    if qso.band:
        # Validate it's a known band name
        band = band_from_n1mm_name(qso.band)
        if band:
            return band.name
        # Try it as a plain name (e.g. "40m" not "40M")
        from app.core.band_plan import get_band
        b = get_band(qso.band)
        if b:
            return b.name
        log.debug("Unknown band string '%s' in QSO, will try frequency.", qso.band)

    # 2. Derive from frequency
    if qso.frequency_hz is not None:
        from app.core.band_plan import band_from_frequency_hz
        band = band_from_frequency_hz(qso.frequency_hz)
        if band:
            log.debug(
                "Derived band %s from frequency %.0f Hz", band.name, qso.frequency_hz
            )
            return band.name

    log.debug(
        "Cannot resolve band for QSO %s (band=%r, freq=%r)",
        qso.original_callsign, qso.band, qso.frequency_hz,
    )
    return None
