"""
app/core/band_plan.py
=====================
Amateur radio band definitions for N1MM Field Day Tracker.

Supported bands
---------------
160m, 80m, 40m, 30m, 20m, 15m, 12m, 10m, 6m, 2m, 70cm

Frequency ranges are in **kHz** and follow ITU Region 1 allocations
(Europe/Africa).  N1MM Logger+ reports frequencies in Hz for rxfreq/txfreq
fields, so a conversion helper is included.

Default selected bands for a new field day: 160m, 80m, 40m
All bands are selectable in the field day settings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    """Represents a single amateur radio band.

    Attributes
    ----------
    name:
        Short display name, e.g. ``"40m"``.
    lower_khz:
        Lower edge of the band in kHz.
    upper_khz:
        Upper edge of the band in kHz.
    n1mm_name:
        The band name as N1MM Logger+ may report it (e.g. ``"40M"``).
        Comparison is always case-insensitive.
    """

    name: str
    lower_khz: float
    upper_khz: float
    n1mm_name: str

    def contains_khz(self, freq_khz: float) -> bool:
        """Return True if *freq_khz* falls within this band's range."""
        return self.lower_khz <= freq_khz <= self.upper_khz


# ---------------------------------------------------------------------------
# Band definitions (ITU Region 1)
# ---------------------------------------------------------------------------
# Frequencies in kHz.

ALL_BANDS: tuple[Band, ...] = (
    Band("160m",  1_810.0,   2_000.0,  "160M"),
    Band("80m",   3_500.0,   3_800.0,  "80M"),
    Band("40m",   7_000.0,   7_200.0,  "40M"),
    Band("30m",  10_100.0,  10_150.0,  "30M"),
    Band("20m",  14_000.0,  14_350.0,  "20M"),
    Band("15m",  21_000.0,  21_450.0,  "15M"),
    Band("12m",  24_890.0,  24_990.0,  "12M"),
    Band("10m",  28_000.0,  29_700.0,  "10M"),
    Band("6m",   50_000.0,  52_000.0,  "6M"),
    Band("2m",  144_000.0, 146_000.0,  "2M"),
    Band("70cm",430_000.0, 440_000.0,  "70CM"),
)

# Ordered list of band name strings (used for column ordering in the matrix)
ALL_BAND_NAMES: tuple[str, ...] = tuple(b.name for b in ALL_BANDS)

# Default bands selected when creating a new field day
DEFAULT_SELECTED_BANDS: tuple[str, ...] = ("160m", "80m", "40m")

# Lookup dicts for fast access
_BAND_BY_NAME: dict[str, Band] = {b.name.lower(): b for b in ALL_BANDS}
_BAND_BY_N1MM: dict[str, Band] = {b.n1mm_name.upper(): b for b in ALL_BANDS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_band(name: str) -> Band | None:
    """Look up a band by its display name (case-insensitive).

    Parameters
    ----------
    name:
        Band name, e.g. ``"40m"`` or ``"40M"``.

    Returns
    -------
    Band or None
        The matching Band, or None if not found.
    """
    return _BAND_BY_NAME.get(name.lower())


def band_from_n1mm_name(n1mm_band: str) -> Band | None:
    """Look up a band by the name N1MM Logger+ reports.

    N1MM uses names like ``"40M"``, ``"2M"``, ``"70CM"``.

    Parameters
    ----------
    n1mm_band:
        Band string as received from N1MM.

    Returns
    -------
    Band or None
    """
    return _BAND_BY_N1MM.get(n1mm_band.upper())


def band_from_frequency_hz(freq_hz: float) -> Band | None:
    """Derive the band from a frequency in **Hz** (as reported by N1MM).

    N1MM's ``rxfreq`` / ``txfreq`` fields are in units of **10 Hz**
    (i.e. the value 703000 means 7.030 MHz).  This function accepts
    raw Hz values from N1MM (after multiplying by 10 if needed — see
    ``band_from_n1mm_freq_field``).

    Parameters
    ----------
    freq_hz:
        Frequency in Hz.

    Returns
    -------
    Band or None
    """
    freq_khz = freq_hz / 1_000.0
    for band in ALL_BANDS:
        if band.contains_khz(freq_khz):
            return band
    return None


def band_from_n1mm_freq_field(raw_value: int | float | str) -> Band | None:
    """Derive a band from N1MM's ``rxfreq`` or ``txfreq`` XML field.

    N1MM encodes frequencies in units of **10 Hz**.  For example, the
    value ``703000`` means 7 030 000 Hz = 7.030 MHz (40m band).

    Parameters
    ----------
    raw_value:
        The integer or string value from the N1MM XML ``<rxfreq>`` or
        ``<txfreq>`` element.

    Returns
    -------
    Band or None
    """
    try:
        val = float(raw_value)
    except (TypeError, ValueError):
        return None
    # N1MM unit is 10 Hz → multiply by 10 to get Hz
    freq_hz = val * 10.0
    return band_from_frequency_hz(freq_hz)


def validate_selected_bands(band_names: list[str]) -> tuple[list[str], list[str]]:
    """Split a list of band names into valid and invalid entries.

    Parameters
    ----------
    band_names:
        List of band name strings to validate.

    Returns
    -------
    (valid, invalid)
        Two lists: recognised band names and unrecognised ones.
    """
    valid: list[str] = []
    invalid: list[str] = []
    for name in band_names:
        if name.lower() in _BAND_BY_NAME:
            valid.append(_BAND_BY_NAME[name.lower()].name)  # normalise case
        else:
            invalid.append(name)
    return valid, invalid


def ordered_band_names(selected: list[str]) -> list[str]:
    """Return *selected* band names sorted in the canonical band order.

    Parameters
    ----------
    selected:
        Subset of band names to sort.

    Returns
    -------
    list[str]
        The same names, ordered from lowest to highest frequency band.
    """
    selected_lower = {s.lower() for s in selected}
    return [b.name for b in ALL_BANDS if b.name.lower() in selected_lower]
