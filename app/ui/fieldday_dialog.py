"""
app/ui/fieldday_dialog.py
==========================
Dialog for creating and editing a field day.

Shows all FieldDay fields with validation, band selection checkboxes,
F1 / ? help integration, and OK / Cancel buttons.

Usage::

    # Create new
    dialog = FieldDayDialog(parent, settings=controller.settings)
    if dialog.result:
        controller.create_fieldday(dialog.result)

    # Edit existing
    dialog = FieldDayDialog(
        parent,
        fieldday=controller.fieldday,
        settings=controller.settings,
    )
    if dialog.result:
        controller.update_fieldday(dialog.result)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timezone
from typing import Optional

from app.core.band_plan import ALL_BAND_NAMES, ordered_band_names
from app.core.models import AppSettings, FieldDay
from app.i18n.translations import t
from app.ui.help_system import HelpTopic, add_help_button, bind_f1


class FieldDayDialog:
    """Modal dialog for creating or editing a field day.

    Parameters
    ----------
    parent:
        Parent Tkinter widget.
    fieldday:
        Existing FieldDay to edit, or None to create a new one.
    settings:
        Current AppSettings (provides defaults for new field days).
    """

    def __init__(
        self,
        parent: tk.Widget,
        fieldday: Optional[FieldDay] = None,
        settings: Optional[AppSettings] = None,
    ) -> None:
        self.result: Optional[FieldDay] = None
        self._editing = fieldday is not None
        self._settings = settings or AppSettings()

        # Build a working copy
        self._fd = FieldDay()
        if fieldday:
            d = fieldday.to_dict()
            self._fd = FieldDay.from_dict(d)

        self._win = tk.Toplevel(parent)
        title = t("dlg_edit_fieldday_title") if self._editing else t("dlg_new_fieldday_title")
        self._win.title(title)
        self._win.resizable(False, False)
        self._win.grab_set()

        bind_f1(self._win, HelpTopic.FIELD_DAY_SETTINGS)
        self._build_ui()
        self._populate()

        # Centre over parent
        self._win.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        dw = self._win.winfo_width()
        dh = self._win.winfo_height()
        self._win.geometry(
            f"+{max(0, px + (pw - dw)//2)}+{max(0, py + (ph - dh)//2)}"
        )
        self._win.wait_window()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 4}

        # ── Notebook with two tabs ──────────────────────────────────
        nb = ttk.Notebook(self._win)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tab_general = tk.Frame(nb, padx=8, pady=8)
        tab_advanced = tk.Frame(nb, padx=8, pady=8)
        nb.add(tab_general, text="  General  ")
        nb.add(tab_advanced, text="  Advanced  ")

        self._build_general_tab(tab_general, pad)
        self._build_advanced_tab(tab_advanced, pad)

        # ── Bottom buttons ──────────────────────────────────────────
        btn_frame = tk.Frame(self._win)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        add_help_button(btn_frame, HelpTopic.FIELD_DAY_SETTINGS,
                        row=0, column=0, padx=4)

        tk.Button(
            btn_frame, text=t("btn_save"), width=10,
            command=self._on_save, bg="#1e3a5f", fg="white",
        ).grid(row=0, column=2, padx=4)

        tk.Button(
            btn_frame, text=t("btn_cancel"), width=10,
            command=self._win.destroy,
        ).grid(row=0, column=3, padx=4)

        btn_frame.columnconfigure(1, weight=1)

    def _build_general_tab(self, parent: tk.Frame, pad: dict) -> None:
        r = 0

        def lbl(text: str) -> None:
            nonlocal r
            tk.Label(parent, text=text, anchor=tk.W).grid(
                row=r, column=0, sticky=tk.W, **pad)

        def entry(var: tk.StringVar, width: int = 35) -> ttk.Entry:
            e = ttk.Entry(parent, textvariable=var, width=width)
            e.grid(row=r, column=1, columnspan=2, sticky=tk.EW, **pad)
            return e

        # Name
        self._var_name = tk.StringVar()
        lbl(t("lbl_fieldday_name") + " *")
        entry(self._var_name)
        if self._editing:
            # Name cannot be changed after creation
            parent.grid_slaves(row=r, column=1)[0].config(state="disabled")
        r += 1

        # Location
        self._var_location = tk.StringVar()
        lbl(t("lbl_location"))
        entry(self._var_location)
        r += 1

        # Event callsign
        self._var_callsign = tk.StringVar()
        lbl(t("lbl_event_callsign"))
        entry(self._var_callsign, width=20)
        r += 1

        # Organizer
        self._var_organizer = tk.StringVar()
        lbl(t("lbl_organizer"))
        entry(self._var_organizer)
        r += 1

        # Start UTC
        self._var_start = tk.StringVar()
        lbl(t("lbl_start_utc") + " *")
        frm_start = tk.Frame(parent)
        frm_start.grid(row=r, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Entry(frm_start, textvariable=self._var_start, width=22).pack(side=tk.LEFT)
        tk.Label(frm_start, text="  YYYY-MM-DD HH:MM:SS", fg="grey").pack(side=tk.LEFT)
        add_help_button(frm_start, HelpTopic.FIELD_DAY_PERIOD).pack(side=tk.LEFT, padx=4)
        r += 1

        # End UTC
        self._var_end = tk.StringVar()
        lbl(t("lbl_end_utc") + " *")
        frm_end = tk.Frame(parent)
        frm_end.grid(row=r, column=1, columnspan=2, sticky=tk.W, **pad)
        ttk.Entry(frm_end, textvariable=self._var_end, width=22).pack(side=tk.LEFT)
        tk.Label(frm_end, text="  YYYY-MM-DD HH:MM:SS", fg="grey").pack(side=tk.LEFT)
        r += 1

        # Display timezone
        self._var_tz = tk.StringVar(value="UTC")
        lbl(t("lbl_display_timezone"))
        entry(self._var_tz, width=25)
        r += 1

        # Remarks
        self._var_remarks = tk.StringVar()
        lbl(t("lbl_remarks"))
        entry(self._var_remarks)
        r += 1

        # Band selection
        tk.Label(parent, text=t("lbl_selected_bands"), anchor=tk.W).grid(
            row=r, column=0, sticky=tk.NW, **pad)

        band_frame = tk.Frame(parent)
        band_frame.grid(row=r, column=1, columnspan=2, sticky=tk.W, **pad)

        self._band_vars: dict[str, tk.BooleanVar] = {}
        for i, band in enumerate(ALL_BAND_NAMES):
            var = tk.BooleanVar(value=False)
            self._band_vars[band] = var
            cb = tk.Checkbutton(band_frame, text=band, variable=var)
            cb.grid(row=i // 4, column=i % 4, sticky=tk.W, padx=6)

        help_btn = tk.Button(
            band_frame, text="?", width=2,
            font=("Segoe UI", 9, "bold"), fg="#1e3a5f",
            relief=tk.FLAT, cursor="question_arrow",
            command=lambda: __import__(
                "app.ui.help_system", fromlist=["show_help"]
            ).show_help(parent, HelpTopic.FIELD_DAY_BANDS),
        )
        help_btn.grid(
            row=len(ALL_BAND_NAMES) // 4 + 1, column=0,
            columnspan=4, sticky=tk.W, pady=4,
        )
        r += 1

        parent.columnconfigure(1, weight=1)

    def _build_advanced_tab(self, parent: tk.Frame, pad: dict) -> None:
        r = 0

        def lbl(text: str) -> None:
            nonlocal r
            tk.Label(parent, text=text, anchor=tk.W).grid(
                row=r, column=0, sticky=tk.W, **pad)

        # N1MM host override
        self._var_n1mm_host = tk.StringVar()
        lbl(t("lbl_n1mm_host"))
        frm = tk.Frame(parent)
        frm.grid(row=r, column=1, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self._var_n1mm_host, width=18).pack(side=tk.LEFT)
        tk.Label(frm, text="  (leave blank = use global setting)", fg="grey").pack(side=tk.LEFT)
        r += 1

        # N1MM port override
        self._var_n1mm_port = tk.StringVar()
        lbl(t("lbl_n1mm_port"))
        frm2 = tk.Frame(parent)
        frm2.grid(row=r, column=1, sticky=tk.W, **pad)
        ttk.Entry(frm2, textvariable=self._var_n1mm_port, width=8).pack(side=tk.LEFT)
        tk.Label(frm2, text="  (0 = use global setting)", fg="grey").pack(side=tk.LEFT)
        add_help_button(frm2, HelpTopic.N1MM_UDP).pack(side=tk.LEFT, padx=4)
        r += 1

        # Freshness threshold override
        self._var_freshness = tk.StringVar()
        lbl(t("lbl_freshness_threshold"))
        frm3 = tk.Frame(parent)
        frm3.grid(row=r, column=1, sticky=tk.W, **pad)
        ttk.Entry(frm3, textvariable=self._var_freshness, width=8).pack(side=tk.LEFT)
        tk.Label(frm3, text="  (0 = use global setting)", fg="grey").pack(side=tk.LEFT)
        r += 1

        # Strict callsign matching override
        self._var_strict = tk.BooleanVar()
        lbl(t("lbl_strict_matching"))
        frm4 = tk.Frame(parent)
        frm4.grid(row=r, column=1, sticky=tk.W, **pad)
        tk.Checkbutton(frm4, variable=self._var_strict).pack(side=tk.LEFT)
        tk.Label(frm4, text=t("lbl_strict_matching_hint"), fg="grey",
                 font=("Segoe UI", 8), wraplength=320, justify=tk.LEFT).pack(side=tk.LEFT, padx=4)
        add_help_button(frm4, HelpTopic.CALLSIGN_MATCHING).pack(side=tk.LEFT, padx=4)
        r += 1

        # Operator notes
        tk.Label(parent, text=t("lbl_operator_notes"), anchor=tk.NW).grid(
            row=r, column=0, sticky=tk.NW, **pad)
        self._txt_notes = tk.Text(parent, width=40, height=5,
                                  wrap=tk.WORD, font=("Segoe UI", 9))
        self._txt_notes.grid(row=r, column=1, sticky=tk.EW, **pad)
        r += 1

        parent.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Populate from existing FieldDay
    # ------------------------------------------------------------------

    def _populate(self) -> None:
        fd = self._fd
        self._var_name.set(fd.name)
        self._var_location.set(fd.location)
        self._var_callsign.set(fd.event_callsign)
        self._var_organizer.set(fd.organizer)
        self._var_tz.set(fd.display_timezone or "UTC")
        self._var_remarks.set(fd.remarks)
        self._var_n1mm_host.set(fd.n1mm_udp_host)
        self._var_n1mm_port.set(str(fd.n1mm_udp_port) if fd.n1mm_udp_port else "")
        self._var_freshness.set(
            str(fd.freshness_threshold_seconds) if fd.freshness_threshold_seconds else ""
        )
        self._var_strict.set(fd.strict_callsign_matching)

        # Timestamps
        def _fmt(iso: str) -> str:
            if not iso:
                return ""
            try:
                dt = datetime.fromisoformat(iso)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return iso

        self._var_start.set(_fmt(fd.start_utc))
        self._var_end.set(_fmt(fd.end_utc))

        # Bands
        selected = set(fd.selected_bands) if fd.selected_bands else set(
            self._settings.default_selected_bands
        )
        for band, var in self._band_vars.items():
            var.set(band in selected)

        # Operator notes
        if hasattr(self, "_txt_notes"):
            self._txt_notes.delete("1.0", tk.END)
            self._txt_notes.insert("1.0", fd.operator_notes or "")

    # ------------------------------------------------------------------
    # Save / validate
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        fd = self._fd

        # Name
        name = self._var_name.get().strip()
        if not name:
            messagebox.showerror(t("dlg_new_fieldday_title"), t("msg_name_required"))
            return
        fd.name = name

        # Parse timestamps
        start_str = self._var_start.get().strip()
        end_str = self._var_end.get().strip()

        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            fd.start_utc = start_dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            messagebox.showerror(
                t("dlg_new_fieldday_title"),
                f"Invalid start time format.\nExpected: YYYY-MM-DD HH:MM:SS",
            )
            return

        try:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            fd.end_utc = end_dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            messagebox.showerror(
                t("dlg_new_fieldday_title"),
                f"Invalid end time format.\nExpected: YYYY-MM-DD HH:MM:SS",
            )
            return

        if not fd.is_valid_period():
            messagebox.showerror(
                t("dlg_new_fieldday_title"), t("msg_end_before_start")
            )
            return

        # Other fields
        fd.location = self._var_location.get().strip()
        fd.event_callsign = self._var_callsign.get().strip()
        fd.organizer = self._var_organizer.get().strip()
        fd.display_timezone = self._var_tz.get().strip() or "UTC"
        fd.remarks = self._var_remarks.get().strip()

        # Bands
        fd.selected_bands = [
            band for band, var in self._band_vars.items() if var.get()
        ]
        if not fd.selected_bands:
            messagebox.showwarning(
                t("dlg_new_fieldday_title"),
                "Please select at least one band.",
            )
            return
        from app.core.band_plan import ordered_band_names
        fd.selected_bands = ordered_band_names(fd.selected_bands)

        # Advanced
        fd.n1mm_udp_host = self._var_n1mm_host.get().strip()
        try:
            fd.n1mm_udp_port = int(self._var_n1mm_port.get() or "0")
        except ValueError:
            fd.n1mm_udp_port = 0
        try:
            fd.freshness_threshold_seconds = int(self._var_freshness.get() or "0")
        except ValueError:
            fd.freshness_threshold_seconds = 0
        fd.strict_callsign_matching = self._var_strict.get()
        if hasattr(self, "_txt_notes"):
            fd.operator_notes = self._txt_notes.get("1.0", tk.END).strip()

        self.result = fd
        self._win.destroy()
