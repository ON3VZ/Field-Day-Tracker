"""
app/core/status.py
==================
Status definitions for station-band combinations.

Each station+band pair has exactly one status at any moment.
Manual overrides always take priority over automatic N1MM data.

Status hierarchy (highest priority first)
------------------------------------------
1. excluded          – operator manually excluded this combination
2. manual_not_worked – operator manually marked as not worked
3. manual_worked     – operator manually marked as worked
4. worked_by_n1mm    – N1MM logged at least one QSO for this callsign+band
5. not_worked        – no QSO found, no override

Colour defaults
---------------
Colours are stored as hex strings (#rrggbb) and can be overridden in
app_settings.json under the ``status_colors`` key.
"""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    """Possible statuses for a station+band combination."""

    NOT_WORKED = "not_worked"
    WORKED_BY_N1MM = "worked_by_n1mm"
    MANUAL_WORKED = "manual_worked"
    MANUAL_NOT_WORKED = "manual_not_worked"
    EXCLUDED = "excluded"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def is_worked(self) -> bool:
        """Return True if this status counts as 'worked' for statistics."""
        return self in (Status.WORKED_BY_N1MM, Status.MANUAL_WORKED)

    def is_manual(self) -> bool:
        """Return True if this status was set by a manual override."""
        return self in (
            Status.MANUAL_WORKED,
            Status.MANUAL_NOT_WORKED,
            Status.EXCLUDED,
        )

    def is_excluded(self) -> bool:
        """Return True if this combination is excluded from statistics."""
        return self == Status.EXCLUDED


# ---------------------------------------------------------------------------
# Override action names (used in UI and stored in overrides.json)
# ---------------------------------------------------------------------------

class OverrideAction(str, Enum):
    """Actions a user can apply as a manual override."""

    MANUAL_WORKED = "manual_worked"
    MANUAL_NOT_WORKED = "manual_not_worked"
    EXCLUDED = "excluded"
    CLEAR = "clear"          # removes the override, restores automatic status


# ---------------------------------------------------------------------------
# Default colour palette
# ---------------------------------------------------------------------------

DEFAULT_STATUS_COLORS: dict[str, str] = {
    Status.NOT_WORKED.value:       "#FFFFFF",   # white  – not yet worked
    Status.WORKED_BY_N1MM.value:   "#4CAF50",   # green  – logged by N1MM
    Status.MANUAL_WORKED.value:    "#1B5E20",   # dark green – manually worked
    Status.MANUAL_NOT_WORKED.value: "#FFC107",  # amber  – manually not worked
    Status.EXCLUDED.value:         "#9E9E9E",   # grey   – excluded
}

# Foreground (text) colours that contrast with the backgrounds above
DEFAULT_STATUS_FG_COLORS: dict[str, str] = {
    Status.NOT_WORKED.value:        "#333333",
    Status.WORKED_BY_N1MM.value:    "#FFFFFF",
    Status.MANUAL_WORKED.value:     "#FFFFFF",
    Status.MANUAL_NOT_WORKED.value: "#333333",
    Status.EXCLUDED.value:          "#FFFFFF",
}

# Short display symbols shown inside each matrix cell
STATUS_SYMBOLS: dict[str, str] = {
    Status.NOT_WORKED.value:        "",
    Status.WORKED_BY_N1MM.value:    "✓",
    Status.MANUAL_WORKED.value:     "✓*",
    Status.MANUAL_NOT_WORKED.value: "✗",
    Status.EXCLUDED.value:          "—",
}


def resolve_colors(
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return the effective background colour map, applying any user overrides.

    Parameters
    ----------
    overrides:
        Dict mapping status value strings to hex colour strings, as loaded
        from ``app_settings.json["status_colors"]``.  Keys not present in
        ``overrides`` keep the default colour.
    """
    colors = dict(DEFAULT_STATUS_COLORS)
    if overrides:
        for key, value in overrides.items():
            if key in colors and isinstance(value, str) and value.startswith("#"):
                colors[key] = value
    return colors
