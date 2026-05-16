"""
app/core/callsign.py
====================
Callsign normalisation for N1MM Field Day Tracker.

Two matching modes
------------------
strict=False (default)
    Common portable/mobile/QRP suffixes are stripped before comparison.
    ``ON3VZ``, ``ON3VZ/P``, ``ON3VZ/M``, ``ON3VZ/QRP`` all normalise to
    ``ON3VZ``.

strict=True
    The callsign is only upper-cased and whitespace-stripped.  No suffix
    removal takes place.  ``ON3VZ/P`` != ``ON3VZ``.

The normalisation logic lives here, isolated from the UI and the sync
engine, so it can be unit-tested independently.

Strippable suffixes (non-strict mode)
--------------------------------------
/P    – portable
/M    – mobile
/MM   – maritime mobile
/AM   – aeronautical mobile
/QRP  – low power
/A    – alternative (some contest usage)
/0 … /9 – DXCC-style district suffixes (e.g. W1AW/4)

A suffix is only stripped when it appears after a ``/`` that follows at
least two characters of base callsign.  This prevents stripping things
like ``F/ON3VZ`` (a DXCC prefix) where the slash is at the *start*.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Known portable/operational suffixes to strip in non-strict mode.
# Order matters: longest first so /MM is tried before /M.
# ---------------------------------------------------------------------------
_STRIPPABLE_SUFFIXES: tuple[str, ...] = (
    "/QRP",
    "/MM",
    "/AM",
    "/PM",
    "/P",
    "/M",
    "/A",
    "/B",
)

# District suffix pattern: /0 through /9
_DISTRICT_SUFFIX_RE = re.compile(r"/\d$")

# Minimum base length before a trailing suffix is considered strippable.
# Prevents stripping "F/ON3VZ" → we require at least 2 chars before "/".
_MIN_BASE_LENGTH = 2


def normalize(callsign: str, *, strict: bool = False) -> str:
    """Return the normalised form of *callsign*.

    Parameters
    ----------
    callsign:
        Raw callsign string as received from N1MM or the CSV file.
    strict:
        When True, only upper-case and strip whitespace.
        When False (default), also remove common portable/mobile suffixes.

    Returns
    -------
    str
        Normalised callsign.  Empty string if input is empty/whitespace.

    Examples
    --------
    >>> normalize("on3vz/p")
    'ON3VZ'
    >>> normalize("on3vz/p", strict=True)
    'ON3VZ/P'
    >>> normalize("ON3VZ/MM")
    'ON3VZ'
    >>> normalize("ON3VZ/4")
    'ON3VZ'
    >>> normalize("F/ON3VZ")          # DXCC prefix – no strip
    'F/ON3VZ'
    >>> normalize("")
    ''
    """
    if not callsign or not callsign.strip():
        return ""

    call = callsign.strip().upper()

    if strict:
        return call

    # --- Non-strict: strip trailing suffixes ---

    # District suffix (/0–/9)
    call = _DISTRICT_SUFFIX_RE.sub("", call)

    # Known text suffixes
    for suffix in _STRIPPABLE_SUFFIXES:
        if call.endswith(suffix):
            base = call[: -len(suffix)]
            if len(base) >= _MIN_BASE_LENGTH:
                call = base
                break  # only strip one suffix

    return call


def matches(
    callsign_a: str,
    callsign_b: str,
    *,
    strict: bool = False,
) -> bool:
    """Return True if two callsigns refer to the same station.

    Both sides are normalised with the same *strict* setting before
    comparison, so the caller does not need to normalise beforehand.

    Parameters
    ----------
    callsign_a:
        First callsign (e.g. from the station CSV).
    callsign_b:
        Second callsign (e.g. from an N1MM QSO).
    strict:
        Matching mode passed through to :func:`normalize`.

    Returns
    -------
    bool

    Examples
    --------
    >>> matches("ON3VZ", "ON3VZ/P")
    True
    >>> matches("ON3VZ", "ON3VZ/P", strict=True)
    False
    >>> matches("ON3VZ", "on3vz")
    True
    """
    return normalize(callsign_a, strict=strict) == normalize(callsign_b, strict=strict)


def is_valid_callsign(callsign: str) -> bool:
    """Return True if *callsign* looks like a plausible amateur radio callsign.

    This is a lightweight sanity check for CSV import and manual entry.
    It does NOT validate against the full ITU callsign format — just checks
    that the string is non-empty, contains at least one letter and one digit,
    and contains only allowed characters.

    Parameters
    ----------
    callsign:
        Callsign string to validate (will be stripped/uppercased internally).

    Returns
    -------
    bool

    Examples
    --------
    >>> is_valid_callsign("ON3VZ")
    True
    >>> is_valid_callsign("ON3VZ/P")
    True
    >>> is_valid_callsign("")
    False
    >>> is_valid_callsign("INVALID!!")
    False
    """
    if not callsign or not callsign.strip():
        return False
    call = callsign.strip().upper()
    # Allowed characters: letters, digits, slash
    if not re.match(r"^[A-Z0-9/]+$", call):
        return False
    # Must have at least one letter and one digit
    if not re.search(r"[A-Z]", call):
        return False
    if not re.search(r"[0-9]", call):
        return False
    # Must be at least 3 characters
    if len(call) < 3:
        return False
    return True
