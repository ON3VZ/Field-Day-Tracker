"""
app/storage/json_store.py
=========================
Atomic JSON file read/write for N1MM Field Day Tracker.

Why atomic writes?
------------------
A plain ``json.dump()`` to the target file risks leaving the file half-written
if the process is interrupted (power loss, crash).  The safe pattern is:

1. Write the new content to a *temporary* file in the same directory.
2. Validate that the temporary file is valid JSON.
3. Replace the original file with the temporary file (atomic on most OSes).

This guarantees that the original file is either fully replaced or untouched.

Public API
----------
read_json(path)          → dict | list | None
write_json(path, data)   → None  (raises on failure)
read_json_list(path)     → list
ensure_dir(path)         → None
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def read_json(path: Path | str) -> Any:
    """Read and parse a JSON file.

    Parameters
    ----------
    path:
        Path to the JSON file.

    Returns
    -------
    Parsed JSON value (usually dict or list), or ``None`` if the file does
    not exist or cannot be parsed.  A warning is logged for parse errors.
    """
    path = Path(path)
    if not path.exists():
        log.debug("JSON file not found: %s", path)
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        log.warning("Corrupt JSON file %s: %s", path, exc)
        return None
    except OSError as exc:
        log.warning("Cannot read %s: %s", path, exc)
        return None


def read_json_list(path: Path | str) -> list:
    """Read a JSON file that should contain a list.

    Returns an empty list if the file does not exist, is empty, or contains
    something other than a list.
    """
    data = read_json(path)
    if isinstance(data, list):
        return data
    if data is not None:
        log.warning("Expected a JSON list in %s, got %s", path, type(data).__name__)
    return []


def read_json_dict(path: Path | str) -> dict:
    """Read a JSON file that should contain a dict.

    Returns an empty dict if the file does not exist, is empty, or contains
    something other than a dict.
    """
    data = read_json(path)
    if isinstance(data, dict):
        return data
    if data is not None:
        log.warning("Expected a JSON dict in %s, got %s", path, type(data).__name__)
    return {}


# ---------------------------------------------------------------------------
# Write (atomic)
# ---------------------------------------------------------------------------

def write_json(path: Path | str, data: Any, *, indent: int = 2) -> None:
    """Write *data* to *path* as JSON using an atomic write.

    Steps
    -----
    1. Serialise *data* to a JSON string (raises ``TypeError`` for
       non-serialisable values).
    2. Write the string to a temporary file in the same directory as *path*.
    3. Re-read and parse the temporary file to verify it is valid JSON.
    4. Replace *path* with the temporary file.

    Parameters
    ----------
    path:
        Destination file path.  Parent directories are created automatically.
    data:
        Any JSON-serialisable value.
    indent:
        Indentation level for pretty-printing (default 2).

    Raises
    ------
    TypeError
        If *data* contains non-serialisable values.
    OSError
        If the file cannot be written or replaced.
    ValueError
        If the written file fails JSON validation (should never happen).
    """
    path = Path(path)
    ensure_dir(path.parent)

    # --- Serialise ---
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)

    # --- Write to temp file in the same directory ---
    tmp_path: Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".tmp.json",
        )
        tmp_path = Path(tmp_str)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json_str)

        # --- Validate ---
        with tmp_path.open(encoding="utf-8") as fh:
            json.load(fh)  # raises JSONDecodeError if invalid

        # --- Atomic replace ---
        tmp_path.replace(path)
        log.debug("Wrote %s (%d bytes)", path, len(json_str))

    except Exception:
        # Clean up temp file on any failure
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def ensure_dir(path: Path | str) -> None:
    """Create *path* and all parents if they do not exist."""
    Path(path).mkdir(parents=True, exist_ok=True)
