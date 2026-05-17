"""
app/main.py
===========
Entry point for the N1MM Field Day Tracker application.

In development mode, run from the project root:
    python app/main.py

In a PyInstaller build the generated executable calls this file directly.

Responsibilities
----------------
- Locate the application data root (sibling to the executable / project root)
- Bootstrap logging
- Load app-level settings
- Apply the saved UI language
- Launch the main Tkinter window
"""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from pathlib import Path


# ---------------------------------------------------------------------------
# Resolve the application data root
# ---------------------------------------------------------------------------
def _resolve_app_root() -> Path:
    """Return the directory where app_settings.json and fielddays/ live.

    When running from source: the *project* root (parent of ``app/``).
    When running as a PyInstaller .exe: directory containing the executable.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller sets sys.frozen and sys._MEIPASS
        return Path(sys.executable).parent
    # Running from source: go up one level from app/
    return Path(__file__).parent.parent


APP_ROOT: Path = _resolve_app_root()

# ---------------------------------------------------------------------------
# Bootstrap logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("n1mm_fdt")
log.info("Application root: %s", APP_ROOT)


# ---------------------------------------------------------------------------
# Deferred imports (after sys.path is ready)
# ---------------------------------------------------------------------------
# Make sure "app" package is importable when launched as `python app/main.py`
_src_root = Path(__file__).parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))


def _bootstrap() -> None:
    """Initialise controller and start the GUI."""
    from app.i18n.translations import set_language
    from app.app_controller import AppController
    from app.ui.main_window import MainWindow

    # Controller owns all state
    controller = AppController(APP_ROOT)
    controller.startup()   # loads settings, opens last field day, starts UDP

    # GUI
    root = tk.Tk()
    MainWindow(root, controller)
    root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        _bootstrap()
    except Exception:  # noqa: BLE001
        log.exception("Fatal error during startup.")
        sys.exit(1)
