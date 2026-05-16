"""
app/ui/main_window.py
=====================
Main application window for N1MM Field Day Tracker.

This is the *placeholder* version built in Step 1.  It shows:
- Window title and minimum size
- Menu bar (File / View / Tools / Help) with stub callbacks
- Header area: active field day name + period
- Centre placeholder with "no active field day" message
- Status bar: N1MM connection indicator + last-received timestamp

Later steps will replace the placeholder centre with the real MatrixView,
wire up dialogs, and connect the UDP listener.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from app.i18n.translations import t

log = logging.getLogger(__name__)


class MainWindow:
    """Root application window."""

    # Minimum window dimensions (pixels)
    MIN_WIDTH = 900
    MIN_HEIGHT = 600

    def __init__(
        self,
        root: tk.Tk,
        app_root: Path,
        initial_settings: dict,
    ) -> None:
        self._root = root
        self._app_root = app_root
        self._settings = initial_settings

        self._setup_window()
        self._build_menu()
        self._build_header()
        self._build_centre()
        self._build_status_bar()

        log.info("MainWindow ready.")

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self._root.title(t("app_title"))
        self._root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self._root.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}")
        # Graceful close
        self._root.protocol("WM_DELETE_WINDOW", self._on_quit)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self._root)

        # ── File ────────────────────────────────────────────────────────
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label=t("menu_new_fieldday"), command=self._stub("new_fieldday"))
        file_menu.add_command(label=t("menu_open_fieldday"), command=self._stub("open_fieldday"))
        file_menu.add_command(label=t("menu_switch_fieldday"), command=self._stub("switch_fieldday"))
        file_menu.add_command(label=t("menu_edit_fieldday"), command=self._stub("edit_fieldday"))
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_import_csv"), command=self._stub("import_csv"))
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_export_csv"), command=self._stub("export_csv"))
        file_menu.add_command(label=t("menu_export_pdf"), command=self._stub("export_pdf"))
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_quit"), command=self._on_quit)
        menubar.add_cascade(label=t("menu_file"), menu=file_menu)

        # ── View ────────────────────────────────────────────────────────
        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label=t("menu_refresh"), command=self._stub("refresh"))
        menubar.add_cascade(label=t("menu_view"), menu=view_menu)

        # ── Tools ───────────────────────────────────────────────────────
        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label=t("menu_manual_sync"), command=self._stub("manual_sync"))
        tools_menu.add_command(label=t("menu_add_station"), command=self._stub("add_station"))
        tools_menu.add_separator()
        tools_menu.add_command(label=t("menu_settings"), command=self._stub("settings"))
        menubar.add_cascade(label=t("menu_tools"), menu=tools_menu)

        # ── Help ────────────────────────────────────────────────────────
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label=t("menu_about"), command=self._show_about)
        menubar.add_cascade(label=t("menu_help"), menu=help_menu)

        self._root.config(menu=menubar)

    # ------------------------------------------------------------------
    # Header (active field day info)
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        header = tk.Frame(self._root, bg="#1e3a5f", pady=8)
        header.pack(fill=tk.X)

        # Left side: active field day label + name
        left = tk.Frame(header, bg="#1e3a5f")
        left.pack(side=tk.LEFT, padx=12)

        tk.Label(
            left,
            text=t("lbl_active_fieldday"),
            bg="#1e3a5f",
            fg="#aac4e0",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W)

        self._lbl_fieldday_name = tk.Label(
            left,
            text="—",
            bg="#1e3a5f",
            fg="white",
            font=("Segoe UI", 13, "bold"),
        )
        self._lbl_fieldday_name.pack(anchor=tk.W)

        # Right side: period
        right = tk.Frame(header, bg="#1e3a5f")
        right.pack(side=tk.RIGHT, padx=12)

        tk.Label(
            right,
            text=t("lbl_period"),
            bg="#1e3a5f",
            fg="#aac4e0",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.E)

        self._lbl_period = tk.Label(
            right,
            text="—",
            bg="#1e3a5f",
            fg="white",
            font=("Segoe UI", 10),
        )
        self._lbl_period.pack(anchor=tk.E)

    # ------------------------------------------------------------------
    # Centre / main content area (placeholder)
    # ------------------------------------------------------------------

    def _build_centre(self) -> None:
        self._centre = tk.Frame(self._root, bg="#f5f5f5")
        self._centre.pack(fill=tk.BOTH, expand=True)

        self._show_no_fieldday_placeholder()

    def _show_no_fieldday_placeholder(self) -> None:
        """Show the 'no active field day' placeholder in the centre area."""
        for widget in self._centre.winfo_children():
            widget.destroy()

        wrapper = tk.Frame(self._centre, bg="#f5f5f5")
        wrapper.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(
            wrapper,
            text="📋",
            bg="#f5f5f5",
            font=("Segoe UI", 48),
        ).pack()

        tk.Label(
            wrapper,
            text=t("no_active_fieldday"),
            bg="#f5f5f5",
            fg="#555555",
            font=("Segoe UI", 12),
            wraplength=400,
            justify=tk.CENTER,
        ).pack(pady=(8, 16))

        tk.Label(
            wrapper,
            text=t("lbl_n1mm_setup_hint"),
            bg="#f5f5f5",
            fg="#888888",
            font=("Segoe UI", 9),
            justify=tk.CENTER,
        ).pack()

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self._root, bg="#e0e0e0", pady=3)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Left: N1MM connection status
        self._lbl_connection = tk.Label(
            bar,
            text=t("status_waiting"),
            bg="#e0e0e0",
            fg="#666666",
            font=("Segoe UI", 9),
            anchor=tk.W,
        )
        self._lbl_connection.pack(side=tk.LEFT, padx=8)

        # Divider
        tk.Label(bar, text="|", bg="#e0e0e0", fg="#aaaaaa").pack(side=tk.LEFT)

        # Last received timestamp
        self._lbl_last_rx = tk.Label(
            bar,
            text=f"{t('last_received')} {t('never')}",
            bg="#e0e0e0",
            fg="#888888",
            font=("Segoe UI", 9),
        )
        self._lbl_last_rx.pack(side=tk.LEFT, padx=8)

        # Right: app version / subtitle
        tk.Label(
            bar,
            text=t("app_subtitle"),
            bg="#e0e0e0",
            fg="#aaaaaa",
            font=("Segoe UI", 8),
        ).pack(side=tk.RIGHT, padx=8)

    # ------------------------------------------------------------------
    # Public methods (will be called by later components)
    # ------------------------------------------------------------------

    def set_active_fieldday(self, name: str, period: str) -> None:
        """Update the header to reflect the currently active field day."""
        self._lbl_fieldday_name.config(text=name or "—")
        self._lbl_period.config(text=period or "—")

    def set_connection_status(self, status_key: str, color: str = "#666666") -> None:
        """Update the N1MM connection status label.

        Parameters
        ----------
        status_key:
            A translation key such as ``'status_connected'``.
        color:
            Foreground colour for the label.
        """
        self._lbl_connection.config(text=t(status_key), fg=color)

    def set_last_received(self, timestamp_str: str) -> None:
        """Update the 'last received' timestamp in the status bar."""
        self._lbl_last_rx.config(
            text=f"{t('last_received')} {timestamp_str}"
        )

    # ------------------------------------------------------------------
    # Stub helper
    # ------------------------------------------------------------------

    @staticmethod
    def _stub(action: str):
        """Return a callback that shows a placeholder message box."""
        def _callback():
            messagebox.showinfo(
                "Not yet implemented",
                f"'{action}' will be implemented in a future step.",
            )
        return _callback

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        messagebox.showinfo(t("dlg_about_title"), t("dlg_about_text"))

    def _on_quit(self) -> None:
        log.info("Application closing.")
        self._root.destroy()
