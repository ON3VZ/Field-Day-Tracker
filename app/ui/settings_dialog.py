"""
app/ui/settings_dialog.py
==========================
Settings dialog for N1MM Field Day Tracker.

Five tabs
---------
1. General       – language, strict callsign matching, default bands
2. Connection    – N1MM UDP host/port, freshness threshold, setup guide
3. Appearance    – status colours (colour picker per status)
4. CSV Mapping   – map CSV column headers to internal field names
5. Export        – default export folder

Usage::

    from app.ui.settings_dialog import SettingsDialog

    dlg = SettingsDialog(parent, controller)
    # dialog is modal; controller is updated on Save
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.band_plan import ALL_BAND_NAMES, ordered_band_names
from app.core.models import AppSettings
from app.core.status import DEFAULT_STATUS_COLORS, Status
from app.i18n.translations import (
    t, set_language, language_display_names, SUPPORTED_LANGUAGES,
)
from app.ui.help_system import HelpTopic, add_help_button, bind_f1, show_help

if TYPE_CHECKING:
    from app.app_controller import AppController

log = logging.getLogger(__name__)

# Label widths for consistent alignment
_LBL_W = 28


class SettingsDialog:
    """Modal settings dialog.

    Opens modally over *parent*.  On Save the controller's settings are
    updated immediately.  On Cancel nothing changes.

    Parameters
    ----------
    parent:
        Tkinter parent widget.
    controller:
        Live application controller (settings are read and written here).
    """

    def __init__(self, parent: tk.Widget, controller: "AppController") -> None:
        self._parent = parent
        self._ctrl   = controller

        # Work on a deep copy so Cancel is truly non-destructive
        self._settings = AppSettings.from_dict(controller.settings.to_dict())

        self._win = tk.Toplevel(parent)
        self._win.title(t("dlg_settings_title"))
        self._win.resizable(True, True)
        self._win.minsize(560, 480)
        self._win.grab_set()
        bind_f1(self._win, HelpTopic.SETTINGS)

        self._build_ui()
        self._populate()
        self._centre_over_parent()
        self._win.wait_window()

    # =========================================================================
    # UI construction
    # =========================================================================

    def _build_ui(self) -> None:
        # ── Notebook ────────────────────────────────────────────────────────
        self._nb = ttk.Notebook(self._win)
        self._nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._tab_general    = tk.Frame(self._nb, padx=14, pady=10)
        self._tab_connection = tk.Frame(self._nb, padx=14, pady=10)
        self._tab_appearance = tk.Frame(self._nb, padx=14, pady=10)
        self._tab_csv        = tk.Frame(self._nb, padx=14, pady=10)
        self._tab_export     = tk.Frame(self._nb, padx=14, pady=10)
        self._tab_publish    = tk.Frame(self._nb, padx=14, pady=10)

        self._nb.add(self._tab_general,    text=f"  {t('menu_settings').replace('…','')}  ")
        self._nb.add(self._tab_connection, text="  N1MM / UDP  ")
        self._nb.add(self._tab_appearance, text="  Appearance  ")
        self._nb.add(self._tab_csv,        text="  CSV Mapping  ")
        self._nb.add(self._tab_export,     text="  Export  ")
        self._nb.add(self._tab_publish,    text="  📡 Publish  ")

        self._build_tab_general()
        self._build_tab_connection()
        self._build_tab_appearance()
        self._build_tab_csv()
        self._build_tab_export()
        self._build_tab_publish()

        # ── Bottom buttons ───────────────────────────────────────────────────
        btn_bar = tk.Frame(self._win)
        btn_bar.pack(fill=tk.X, padx=8, pady=(0, 8))

        add_help_button(btn_bar, HelpTopic.SETTINGS, row=0, column=0, padx=4)

        tk.Button(
            btn_bar, text=t("btn_save"),
            command=self._on_save,
            width=12, bg="#1e3a5f", fg="white",
            font=("Segoe UI", 9),
        ).grid(row=0, column=2, padx=4)

        tk.Button(
            btn_bar, text=t("btn_cancel"),
            command=self._win.destroy,
            width=12,
        ).grid(row=0, column=3, padx=4)

        btn_bar.columnconfigure(1, weight=1)

    # =========================================================================
    # Tab: General
    # =========================================================================

    def _build_tab_general(self) -> None:
        tab = self._tab_general
        r = 0

        # ── Language ─────────────────────────────────────────────────────────
        self._section(tab, t("lbl_ui_language"), r); r += 1

        lang_frame = tk.Frame(tab)
        lang_frame.grid(row=r, column=0, columnspan=3, sticky=tk.W,
                        padx=(20, 0), pady=(0, 8))
        r += 1

        self._lang_var = tk.StringVar()
        names = language_display_names()
        for code in SUPPORTED_LANGUAGES:
            rb = tk.Radiobutton(
                lang_frame,
                text=names[code],
                variable=self._lang_var,
                value=code,
                command=self._on_language_preview,
                font=("Segoe UI", 10),
            )
            rb.pack(side=tk.LEFT, padx=10)

        add_help_button(lang_frame, HelpTopic.LANGUAGE_SETTING).pack(
            side=tk.LEFT, padx=6)

        self._lang_preview = tk.Label(
            tab, text="", fg="#1e3a5f",
            font=("Segoe UI", 9, "italic"),
        )
        self._lang_preview.grid(
            row=r, column=0, columnspan=3, sticky=tk.W, padx=(20, 0), pady=(0, 12))
        r += 1

        # ── Callsign matching ────────────────────────────────────────────────
        self._section(tab, t("lbl_strict_matching"), r); r += 1

        strict_frame = tk.Frame(tab)
        strict_frame.grid(row=r, column=0, columnspan=3, sticky=tk.W,
                          padx=(20, 0), pady=(0, 4))
        r += 1

        self._strict_var = tk.BooleanVar()
        tk.Checkbutton(
            strict_frame,
            text=t("lbl_strict_matching"),
            variable=self._strict_var,
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT)
        add_help_button(strict_frame, HelpTopic.CALLSIGN_MATCHING).pack(
            side=tk.LEFT, padx=6)

        tk.Label(
            tab,
            text=t("lbl_strict_matching_hint"),
            fg="#666", font=("Segoe UI", 8),
            wraplength=460, justify=tk.LEFT,
        ).grid(row=r, column=0, columnspan=3, sticky=tk.W,
               padx=(20, 0), pady=(0, 16))
        r += 1

        # ── Default selected bands ───────────────────────────────────────────
        self._section(tab, "Default Bands for New Field Days", r); r += 1

        bands_outer = tk.Frame(tab)
        bands_outer.grid(row=r, column=0, columnspan=3, sticky=tk.W,
                         padx=(20, 0), pady=(0, 4))
        r += 1

        self._default_band_vars: dict[str, tk.BooleanVar] = {}
        for i, band in enumerate(ALL_BAND_NAMES):
            v = tk.BooleanVar()
            self._default_band_vars[band] = v
            tk.Checkbutton(
                bands_outer, text=band, variable=v,
                font=("Segoe UI", 9),
            ).grid(row=i // 6, column=i % 6, sticky=tk.W, padx=6, pady=1)

        add_help_button(bands_outer, HelpTopic.FIELD_DAY_BANDS,
                        row=2, column=0, columnspan=2, padx=4, pady=4,
                        sticky=tk.W)

        tab.columnconfigure(0, weight=1)

    # =========================================================================
    # Tab: Connection (N1MM UDP)
    # =========================================================================

    def _build_tab_connection(self) -> None:
        tab = self._tab_connection
        r = 0

        # ── UDP settings ─────────────────────────────────────────────────────
        self._section(tab, "N1MM Logger+ UDP Connection", r); r += 1

        def _row(label_key: str, var: tk.Variable,
                 width: int = 20, hint: str = "",
                 help_topic: HelpTopic | None = None) -> None:
            nonlocal r
            tk.Label(tab, text=t(label_key), width=_LBL_W, anchor=tk.W,
                     font=("Segoe UI", 9)).grid(
                row=r, column=0, sticky=tk.W, pady=3)
            f = tk.Frame(tab)
            f.grid(row=r, column=1, sticky=tk.W, pady=3)
            ttk.Entry(f, textvariable=var, width=width).pack(side=tk.LEFT)
            if hint:
                tk.Label(f, text=hint, fg="#888",
                         font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
            if help_topic:
                add_help_button(f, help_topic).pack(side=tk.LEFT, padx=4)
            r += 1

        self._udp_host_var = tk.StringVar()
        _row("lbl_n1mm_host", self._udp_host_var, 18,
             "(127.0.0.1 = same PC)", HelpTopic.N1MM_UDP)

        self._udp_port_var = tk.StringVar()
        _row("lbl_n1mm_port", self._udp_port_var, 8,
             "(default: 12060)")

        self._freshness_var = tk.StringVar()
        _row("lbl_freshness_threshold", self._freshness_var, 8,
             "seconds")

        # ── Setup guide ──────────────────────────────────────────────────────
        r += 1
        self._section(tab, "N1MM Logger+ Setup Guide", r); r += 1

        guide_frame = tk.Frame(tab, bg="#e8f5e9",
                               relief=tk.GROOVE, bd=1, padx=12, pady=8)
        guide_frame.grid(row=r, column=0, columnspan=2,
                         sticky=tk.EW, pady=4)
        r += 1

        guide_text = (
            "1.  In N1MM Logger+: Config → Configure Ports, Mode Control, Audio, Other\n"
            "2.  Click the 'Broadcast Data' tab\n"
            "3.  Find the 'Contact' row → check Enable\n"
            "4.  Set Destination to:  127.0.0.1:12060\n"
            "5.  Click OK\n\n"
            "Contest to use:  FDREG1"
        )
        tk.Label(
            guide_frame, text=guide_text,
            bg="#e8f5e9", justify=tk.LEFT,
            font=("Courier New", 9),
        ).pack(anchor=tk.W)

        guide_btn = tk.Frame(tab)
        guide_btn.grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=4)
        r += 1
        tk.Button(
            guide_btn, text="📖  Full Setup Help (F1)",
            command=lambda: show_help(self._win, HelpTopic.N1MM_SETUP),
            relief=tk.FLAT, bg="#e8f5e9",
            font=("Segoe UI", 9), cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))

        tab.columnconfigure(1, weight=1)

    # =========================================================================
    # Tab: Appearance (status colours)
    # =========================================================================

    def _build_tab_appearance(self) -> None:
        tab = self._tab_appearance
        r = 0

        self._section(tab, "Status Cell Colours", r); r += 1

        tk.Label(
            tab,
            text="Click a colour swatch to change it.  Changes are previewed immediately.",
            fg="#666", font=("Segoe UI", 8), wraplength=480,
        ).grid(row=r, column=0, columnspan=4, sticky=tk.W,
               padx=(20, 0), pady=(0, 10))
        r += 1

        self._color_vars:   dict[str, tk.StringVar] = {}
        self._color_swatches: dict[str, tk.Label]   = {}

        statuses = [
            (Status.NOT_WORKED,        "not_worked",        t("status_not_worked")),
            (Status.WORKED_BY_N1MM,    "worked_by_n1mm",    t("status_worked_n1mm")),
            (Status.MANUAL_WORKED,     "manual_worked",     t("status_manual_worked")),
            (Status.MANUAL_NOT_WORKED, "manual_not_worked", t("status_manual_not_worked")),
            (Status.EXCLUDED,          "excluded",          t("status_excluded")),
        ]

        for status_enum, key, label in statuses:
            row_frame = tk.Frame(tab, pady=4)
            row_frame.grid(row=r, column=0, columnspan=4,
                           sticky=tk.EW, padx=(20, 0))

            # Colour swatch (clickable)
            swatch = tk.Label(
                row_frame,
                width=6, height=1,
                relief=tk.GROOVE, bd=2,
                cursor="hand2",
                font=("Segoe UI", 10),
            )
            swatch.pack(side=tk.LEFT, padx=(0, 10))
            self._color_swatches[key] = swatch

            # Status label (shows symbol + text)
            symbol = {"not_worked": "·", "worked_by_n1mm": "✓",
                      "manual_worked": "✓*", "manual_not_worked": "✗",
                      "excluded": "—"}.get(key, "")
            tk.Label(
                row_frame,
                text=f"  {symbol}  {label}",
                width=26, anchor=tk.W,
                font=("Segoe UI", 10),
            ).pack(side=tk.LEFT)

            # Hex entry
            var = tk.StringVar()
            self._color_vars[key] = var
            entry = ttk.Entry(row_frame, textvariable=var, width=10)
            entry.pack(side=tk.LEFT, padx=6)
            var.trace_add("write",
                lambda *_, k=key: self._on_color_entry_changed(k))

            # Browse button
            tk.Button(
                row_frame, text="Choose…",
                command=lambda k=key: self._pick_color(k),
                font=("Segoe UI", 8),
                padx=4,
            ).pack(side=tk.LEFT, padx=4)

            r += 1

        # Reset button
        r += 1
        tk.Button(
            tab, text="↺  Reset to defaults",
            command=self._reset_colors,
            font=("Segoe UI", 9),
        ).grid(row=r, column=0, columnspan=4,
               sticky=tk.W, padx=(20, 0), pady=8)
        r += 1

        add_help_button(tab, HelpTopic.STATUS_COLORS,
                        row=r, column=0, sticky=tk.W, padx=(20, 0), pady=4)

        tab.columnconfigure(0, weight=1)

    # =========================================================================
    # Tab: CSV Mapping
    # =========================================================================

    def _build_tab_csv(self) -> None:
        tab = self._tab_csv
        r = 0

        self._section(tab, t("lbl_csv_column_mapping"), r); r += 1

        tk.Label(
            tab,
            text=(
                "Enter the column header name as it appears in your CSV file.\n"
                "Leave blank to use the default (shown in grey)."
            ),
            fg="#666", font=("Segoe UI", 8),
            wraplength=480, justify=tk.LEFT,
        ).grid(row=r, column=0, columnspan=3, sticky=tk.W,
               padx=(20, 0), pady=(0, 10))
        r += 1

        self._csv_map_vars: dict[str, tk.StringVar] = {}

        fields = [
            ("callsign", t("lbl_csv_col_callsign"), "callsign", True),
            ("name",     t("lbl_csv_col_name"),     "name",     False),
            ("club",     t("lbl_csv_col_club"),      "club",     False),
            ("remarks",  t("lbl_csv_col_remarks"),   "remarks",  False),
        ]

        for field, label, default, required in fields:
            tk.Label(tab, text=label + (" *" if required else ""),
                     width=_LBL_W, anchor=tk.W,
                     font=("Segoe UI", 9)).grid(
                row=r, column=0, sticky=tk.W,
                padx=(20, 0), pady=4)

            v = tk.StringVar()
            self._csv_map_vars[field] = v
            entry = ttk.Entry(tab, textvariable=v, width=22)
            entry.grid(row=r, column=1, sticky=tk.W, pady=4)

            tk.Label(tab, text=f"  (default: '{default}')",
                     fg="#aaa", font=("Segoe UI", 8)).grid(
                row=r, column=2, sticky=tk.W)
            r += 1

        # Detect columns button
        r += 1
        detect_frame = tk.Frame(tab)
        detect_frame.grid(row=r, column=0, columnspan=3,
                          sticky=tk.W, padx=(20, 0), pady=8)
        r += 1

        tk.Button(
            detect_frame,
            text=t("btn_detect_columns"),
            command=self._detect_csv_columns,
            font=("Segoe UI", 9), padx=6,
        ).pack(side=tk.LEFT)

        self._detect_result_lbl = tk.Label(
            detect_frame, text="", fg="#1e3a5f",
            font=("Segoe UI", 9), wraplength=340,
        )
        self._detect_result_lbl.pack(side=tk.LEFT, padx=10)

        add_help_button(tab, HelpTopic.CSV_COLUMN_MAPPING,
                        row=r, column=0, sticky=tk.W,
                        padx=(20, 0), pady=4)

        tab.columnconfigure(1, weight=1)

    # =========================================================================
    # Tab: Export
    # =========================================================================

    def _build_tab_publish(self) -> None:
        """GitHub Pages publish settings."""
        tab = self._tab_publish
        r = 0

        self._section(tab, "GitHub Pages Live Publishing", r); r += 1

        tk.Label(
            tab,
            text=(
                "Publish the station matrix as a live web page on GitHub Pages.
"
                "People at home can follow the field day in real time."
            ),
            fg="#1e3a5f", font=("Segoe UI", 9),
            wraplength=480, justify=tk.LEFT,
        ).grid(row=r, column=0, columnspan=3, sticky=tk.W,
               padx=(20, 0), pady=(0, 8))
        r += 1

        def _lbl(text): return tk.Label(tab, text=text, width=_LBL_W,
                                        anchor=tk.W, font=("Segoe UI", 9))

        # Token
        _lbl("GitHub Token (fine-grained)").grid(
            row=r, column=0, sticky=tk.W, padx=(20, 0), pady=4)
        self._gh_token_var = tk.StringVar()
        token_frame = tk.Frame(tab)
        token_frame.grid(row=r, column=1, columnspan=2, sticky=tk.EW, pady=4)
        self._gh_token_entry = ttk.Entry(
            token_frame, textvariable=self._gh_token_var,
            width=40, show="•")
        self._gh_token_entry.pack(side=tk.LEFT)
        self._show_token_var = tk.BooleanVar(value=False)
        def _toggle_show():
            self._gh_token_entry.config(
                show="" if self._show_token_var.get() else "•")
        tk.Checkbutton(token_frame, text="Show",
                       variable=self._show_token_var,
                       command=_toggle_show).pack(side=tk.LEFT, padx=6)
        r += 1

        # Repository
        _lbl("Repository (owner/name)").grid(
            row=r, column=0, sticky=tk.W, padx=(20, 0), pady=4)
        self._gh_repo_var = tk.StringVar()
        repo_frame = tk.Frame(tab)
        repo_frame.grid(row=r, column=1, columnspan=2, sticky=tk.W, pady=4)
        ttk.Entry(repo_frame, textvariable=self._gh_repo_var, width=30).pack(side=tk.LEFT)
        tk.Label(repo_frame, text="  e.g. ON3VZ/Field-Day-Tracker",
                 fg="#888", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        r += 1

        # Pages URL (auto-filled)
        _lbl("Pages URL (auto-detected)").grid(
            row=r, column=0, sticky=tk.W, padx=(20, 0), pady=4)
        self._gh_url_var = tk.StringVar()
        url_frame = tk.Frame(tab)
        url_frame.grid(row=r, column=1, columnspan=2, sticky=tk.W, pady=4)
        ttk.Entry(url_frame, textvariable=self._gh_url_var, width=40).pack(side=tk.LEFT)
        r += 1

        # Validate button
        def _validate():
            from app.exporters.github_pages_publisher import GHPagesPublisher
            token = self._gh_token_var.get().strip()
            repo  = self._gh_repo_var.get().strip()
            ok, msg = GHPagesPublisher.validate_token(token, repo)
            color = "#2e7d32" if ok else "#c62828"
            self._gh_validate_lbl.config(text=msg, fg=color)

        vf = tk.Frame(tab)
        vf.grid(row=r, column=0, columnspan=3, sticky=tk.W, padx=(20, 0), pady=4)
        tk.Button(vf, text="🔑  Validate Token & Repo",
                  command=_validate, font=("Segoe UI", 9), padx=6).pack(side=tk.LEFT)
        self._gh_validate_lbl = tk.Label(vf, text="", font=("Segoe UI", 9))
        self._gh_validate_lbl.pack(side=tk.LEFT, padx=10)
        r += 1

        # Separator
        ttk.Separator(tab, orient=tk.HORIZONTAL).grid(
            row=r, column=0, columnspan=3, sticky=tk.EW,
            padx=(20, 0), pady=8)
        r += 1

        # Auto-publish
        auto_frame = tk.Frame(tab)
        auto_frame.grid(row=r, column=0, columnspan=3, sticky=tk.W,
                        padx=(20, 0), pady=4)
        self._gh_auto_var = tk.BooleanVar()
        tk.Checkbutton(auto_frame, text="Auto-publish on every matrix update",
                       variable=self._gh_auto_var,
                       font=("Segoe UI", 10)).pack(side=tk.LEFT)
        r += 1

        # Interval
        _lbl("Minimum interval between publishes").grid(
            row=r, column=0, sticky=tk.W, padx=(20, 0), pady=4)
        self._gh_interval_var = tk.StringVar()
        if_frame = tk.Frame(tab)
        if_frame.grid(row=r, column=1, sticky=tk.W, pady=4)
        ttk.Entry(if_frame, textvariable=self._gh_interval_var, width=6).pack(side=tk.LEFT)
        tk.Label(if_frame, text=" seconds (min: 30)",
                 fg="#888", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        r += 1

        # Page refresh
        _lbl("Browser auto-refresh on page").grid(
            row=r, column=0, sticky=tk.W, padx=(20, 0), pady=4)
        self._gh_refresh_var = tk.StringVar()
        rf_frame = tk.Frame(tab)
        rf_frame.grid(row=r, column=1, sticky=tk.W, pady=4)
        ttk.Entry(rf_frame, textvariable=self._gh_refresh_var, width=6).pack(side=tk.LEFT)
        tk.Label(rf_frame, text=" seconds (min: 15)",
                 fg="#888", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
        r += 1

        # Last published
        self._gh_last_lbl = tk.Label(
            tab, text="Last published: never",
            fg="#888", font=("Segoe UI", 8))
        self._gh_last_lbl.grid(
            row=r, column=0, columnspan=3, sticky=tk.W,
            padx=(20, 0), pady=(4, 0))
        r += 1

        # Setup instructions
        r += 1
        self._section(tab, "One-time GitHub Pages Setup", r); r += 1

        instructions = (
            "1.  Go to github.com/YOUR_REPO → Settings → Pages\n"
            "2.  Source: Deploy from a branch → branch: gh-pages → / (root)\n"
            "3.  Click Save → copy the URL shown (e.g. https://on3vz.github.io/...)\n"
            "4.  Create a fine-grained token: github.com → Settings →\n"
            "    Developer settings → Personal access tokens → Fine-grained\n"
            "5.  Set expiry to the day AFTER the field day\n"
            "6.  Repository access: only your Field Day repo\n"
            "7.  Permission: Contents → Read and Write (nothing else needed)\n"
            "8.  Paste the token above and click Validate"
        )
        guide = tk.Frame(tab, bg="#fff8e1", relief=tk.GROOVE, bd=1, padx=10, pady=8)
        guide.grid(row=r, column=0, columnspan=3,
                   sticky=tk.EW, padx=(20, 0), pady=4)
        tk.Label(guide, text=instructions, bg="#fff8e1",
                 justify=tk.LEFT, font=("Courier New", 8),
                 ).pack(anchor=tk.W)

        tab.columnconfigure(1, weight=1)

    def _build_tab_export(self) -> None:
        tab = self._tab_export
        r = 0

        self._section(tab, "Export Settings", r); r += 1

        # Export folder
        tk.Label(tab, text=t("lbl_export_folder"),
                 width=_LBL_W, anchor=tk.W,
                 font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky=tk.W, padx=(20, 0), pady=6)

        folder_frame = tk.Frame(tab)
        folder_frame.grid(row=r, column=1, columnspan=2,
                          sticky=tk.EW, pady=6)
        r += 1

        self._export_folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self._export_folder_var,
                  width=36).pack(side=tk.LEFT)
        tk.Button(
            folder_frame, text=t("btn_browse"),
            command=self._browse_export_folder,
            font=("Segoe UI", 9), padx=4,
        ).pack(side=tk.LEFT, padx=6)

        tk.Label(
            tab,
            text="CSV and PDF files will be saved here by default.",
            fg="#666", font=("Segoe UI", 8),
        ).grid(row=r, column=0, columnspan=3,
               sticky=tk.W, padx=(20, 0), pady=(0, 16))
        r += 1

        add_help_button(tab, HelpTopic.CSV_EXPORT,
                        row=r, column=0, sticky=tk.W,
                        padx=(20, 0), pady=4)

        tab.columnconfigure(1, weight=1)

    # =========================================================================
    # Helpers: section headers
    # =========================================================================

    def _section(self, parent: tk.Frame, text: str, row: int) -> None:
        """Add a bold section header row."""
        frm = tk.Frame(parent, bg="#e8eaf6", pady=3)
        frm.grid(row=row, column=0, columnspan=4,
                 sticky=tk.EW, pady=(8, 4))
        tk.Label(frm, text=text, bg="#e8eaf6",
                 fg="#1e3a5f", font=("Segoe UI", 9, "bold"),
                 padx=6).pack(anchor=tk.W)

    # =========================================================================
    # Populate from settings
    # =========================================================================

    def _populate(self) -> None:
        s = self._settings

        # General
        self._lang_var.set(s.ui_language)
        self._strict_var.set(s.strict_callsign_matching)
        for band, var in self._default_band_vars.items():
            var.set(band in (s.default_selected_bands or []))

        # Connection
        self._udp_host_var.set(s.n1mm_udp_host)
        self._udp_port_var.set(str(s.n1mm_udp_port))
        self._freshness_var.set(str(s.freshness_threshold_seconds))

        # Colours
        colors = s.status_colors or {}
        for key, var in self._color_vars.items():
            hex_val = colors.get(key, DEFAULT_STATUS_COLORS.get(key, "#FFFFFF"))
            var.set(hex_val)
            self._update_swatch(key, hex_val)

        # CSV mapping
        mapping = s.csv_column_mapping or {}
        for field, var in self._csv_map_vars.items():
            var.set(mapping.get(field, ""))

        # Export
        self._export_folder_var.set(s.export_folder or "exports")

        # Publish
        from app.security.token_store import TokenStore
        token_plain = TokenStore.decrypt(s.github_token_encrypted)
        self._gh_token_var.set(token_plain)
        self._gh_repo_var.set(s.github_repo)
        self._gh_url_var.set(s.github_pages_url)
        self._gh_auto_var.set(s.github_auto_publish)
        self._gh_interval_var.set(str(s.github_publish_interval_seconds))
        self._gh_refresh_var.set(str(s.github_page_refresh_seconds))
        if s.github_last_published_utc:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(s.github_last_published_utc)
                self._gh_last_lbl.config(
                    text=f"Last published: {dt.strftime('%Y-%m-%d %H:%M UTC')}")
            except ValueError:
                pass

    # =========================================================================
    # Event handlers
    # =========================================================================

    def _on_language_preview(self) -> None:
        code = self._lang_var.get()
        names = language_display_names()
        # Temporarily switch to preview a translated string
        from app.i18n.translations import _STRINGS
        sample_key = "app_title"
        entry = _STRINGS.get(sample_key, {})
        preview = entry.get(code, entry.get("en", ""))
        self._lang_preview.config(
            text=f"Preview: '{preview}'  ({names.get(code, code)})"
        )

    def _on_color_entry_changed(self, key: str) -> None:
        val = self._color_vars[key].get().strip()
        if val.startswith("#") and len(val) in (4, 7):
            try:
                self._win.winfo_rgb(val)  # validates hex colour
                self._update_swatch(key, val)
            except tk.TclError:
                pass

    def _update_swatch(self, key: str, hex_color: str) -> None:
        swatch = self._color_swatches.get(key)
        if swatch:
            try:
                # Choose contrasting text colour
                r, g, b = (
                    int(hex_color[1:3], 16),
                    int(hex_color[3:5], 16),
                    int(hex_color[5:7], 16),
                ) if len(hex_color) == 7 else (255, 255, 255)
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                fg = "#000000" if lum > 140 else "#ffffff"
                swatch.config(bg=hex_color, fg=fg)
            except (ValueError, tk.TclError):
                pass

    def _pick_color(self, key: str) -> None:
        current = self._color_vars[key].get()
        result = colorchooser.askcolor(
            color=current,
            title=f"Choose colour for: {key.replace('_', ' ').title()}",
            parent=self._win,
        )
        if result and result[1]:
            hex_val = result[1].upper()
            self._color_vars[key].set(hex_val)
            self._update_swatch(key, hex_val)

    def _reset_colors(self) -> None:
        for key, hex_val in DEFAULT_STATUS_COLORS.items():
            if key in self._color_vars:
                self._color_vars[key].set(hex_val)
                self._update_swatch(key, hex_val)

    def _detect_csv_columns(self) -> None:
        path = filedialog.askopenfilename(
            title=t("btn_detect_columns"),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=self._win,
        )
        if not path:
            return

        from app.importers.csv_importer import CSVImporter
        cols = CSVImporter.detect_columns(path)
        if cols:
            self._detect_result_lbl.config(
                text=t("msg_columns_detected", columns=", ".join(cols)),
                fg="#1e3a5f",
            )
        else:
            self._detect_result_lbl.config(
                text="No columns detected (empty or unreadable CSV).",
                fg="#c62828",
            )

    def _browse_export_folder(self) -> None:
        folder = filedialog.askdirectory(
            title=t("lbl_export_folder"),
            initialdir=self._export_folder_var.get() or ".",
            parent=self._win,
        )
        if folder:
            self._export_folder_var.set(folder)

    # =========================================================================
    # Save / validate
    # =========================================================================

    def _on_save(self) -> None:
        s = self._settings

        # ── General ──────────────────────────────────────────────────────────
        s.ui_language = self._lang_var.get()
        s.strict_callsign_matching = self._strict_var.get()
        s.default_selected_bands = ordered_band_names([
            band for band, var in self._default_band_vars.items()
            if var.get()
        ])

        # ── Connection ───────────────────────────────────────────────────────
        host = self._udp_host_var.get().strip()
        if not host:
            self._show_error("Connection", "UDP host cannot be empty.")
            self._nb.select(1)
            return
        s.n1mm_udp_host = host

        try:
            port = int(self._udp_port_var.get())
            if not (1024 <= port <= 65535):
                raise ValueError
            s.n1mm_udp_port = port
        except ValueError:
            self._show_error("Connection", t("err_invalid_port"))
            self._nb.select(1)
            return

        try:
            s.freshness_threshold_seconds = int(
                self._freshness_var.get() or "30"
            )
        except ValueError:
            s.freshness_threshold_seconds = 30

        # ── Colours ──────────────────────────────────────────────────────────
        colors: dict[str, str] = {}
        for key, var in self._color_vars.items():
            hex_val = var.get().strip()
            if not (hex_val.startswith("#") and len(hex_val) in (4, 7)):
                self._show_error(
                    "Appearance",
                    f"Invalid colour for '{key}': {hex_val!r}\n"
                    "Use format #RRGGBB (e.g. #4CAF50).",
                )
                self._nb.select(2)
                return
            colors[key] = hex_val.upper()
        s.status_colors = colors

        # ── CSV mapping ───────────────────────────────────────────────────────
        mapping: dict[str, str] = {}
        for field, var in self._csv_map_vars.items():
            val = var.get().strip()
            mapping[field] = val if val else field  # empty → use field name
        if not mapping.get("callsign"):
            self._show_error("CSV Mapping",
                             "The callsign column mapping cannot be empty.")
            self._nb.select(3)
            return
        s.csv_column_mapping = mapping

        # ── Export ────────────────────────────────────────────────────────────
        s.export_folder = self._export_folder_var.get().strip() or "exports"

        # ── GitHub publish ────────────────────────────────────────────────────
        from app.security.token_store import TokenStore
        token_plain = self._gh_token_var.get().strip()
        s.github_token_encrypted = TokenStore.encrypt(token_plain) if token_plain else ""
        s.github_repo = self._gh_repo_var.get().strip()
        s.github_pages_url = self._gh_url_var.get().strip()
        s.github_auto_publish = self._gh_auto_var.get()
        try:
            s.github_publish_interval_seconds = max(
                30, int(self._gh_interval_var.get() or "120"))
        except ValueError:
            s.github_publish_interval_seconds = 120
        try:
            s.github_page_refresh_seconds = max(
                15, int(self._gh_refresh_var.get() or "60"))
        except ValueError:
            s.github_page_refresh_seconds = 60

        # ── Apply to controller ───────────────────────────────────────────────
        self._ctrl.update_settings(s)
        log.info("Settings saved.")
        self._win.destroy()

    def _show_error(self, tab_name: str, message: str) -> None:
        messagebox.showerror(
            f"Settings — {tab_name}", message, parent=self._win
        )

    # =========================================================================
    # Positioning
    # =========================================================================

    def _centre_over_parent(self) -> None:
        self._win.update_idletasks()
        pw = self._parent.winfo_width()
        ph = self._parent.winfo_height()
        px = self._parent.winfo_rootx()
        py = self._parent.winfo_rooty()
        dw = self._win.winfo_width()
        dh = self._win.winfo_height()
        x = max(0, px + (pw - dw) // 2)
        y = max(0, py + (ph - dh) // 2)
        self._win.geometry(f"+{x}+{y}")
