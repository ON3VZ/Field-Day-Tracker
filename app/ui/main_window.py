"""
app/ui/main_window.py
=====================
Main application window for N1MM Field Day Tracker.

Connects the Tkinter UI to :class:`~app.app_controller.AppController`.
All business logic stays in the controller; this file only handles
widget construction, layout and event routing.

Thread safety
-------------
The UDP listener runs in a background thread and calls
``controller.register_on_matrix_changed`` and
``register_on_status_changed`` callbacks on that thread.
We use ``root.after(0, fn)`` to marshal all UI updates back to the
Tkinter main thread.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import TYPE_CHECKING

from app.i18n.translations import t
from app.integrations.n1mm_udp_listener import ListenerStatus
from app.ui.help_system import HelpTopic, bind_f1, show_help

if TYPE_CHECKING:
    from app.app_controller import AppController

log = logging.getLogger(__name__)

_STATUS_COLORS = {
    ListenerStatus.CONNECTED: "#2e7d32",
    ListenerStatus.WAITING:   "#888888",
    ListenerStatus.STALE:     "#e65100",
    ListenerStatus.ERROR:     "#c62828",
    ListenerStatus.STOPPED:   "#888888",
    ListenerStatus.STARTING:  "#888888",
}


class MainWindow:
    """Root application window."""

    MIN_WIDTH  = 960
    MIN_HEIGHT = 620

    def __init__(self, root: tk.Tk, controller: "AppController") -> None:
        self._root = root
        self._ctrl = controller

        self._setup_window()
        self._build_menu()
        self._build_header()
        self._build_toolbar()
        self._build_centre()
        self._build_status_bar()

        self._ctrl.register_on_matrix_changed(self._on_matrix_changed)
        self._ctrl.register_on_status_changed(self._on_status_changed)
        self._ctrl.register_on_fieldday_changed(self._on_fieldday_changed)

        self._matrix_view = None
        self._refresh_header()
        self._refresh_centre()
        bind_f1(self._root, HelpTopic.MAIN_WINDOW)
        log.info("MainWindow ready.")

    def _setup_window(self) -> None:
        self._root.title(t("app_title"))
        self._root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self._root.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}")
        self._root.protocol("WM_DELETE_WINDOW", self._on_quit)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self._root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label=t("menu_new_fieldday"), command=self._cmd_new_fieldday, accelerator="Ctrl+N")
        file_menu.add_command(label=t("menu_open_fieldday"), command=self._cmd_open_fieldday)
        file_menu.add_command(label=t("menu_switch_fieldday"), command=self._cmd_switch_fieldday)
        file_menu.add_command(label=t("menu_edit_fieldday"), command=self._cmd_edit_fieldday)
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_import_csv"), command=self._cmd_import_csv, accelerator="Ctrl+I")
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_export_csv"), command=self._cmd_export_csv)
        file_menu.add_command(label=t("menu_export_pdf"), command=self._cmd_export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label=t("menu_quit"), command=self._on_quit, accelerator="Alt+F4")
        menubar.add_cascade(label=t("menu_file"), menu=file_menu)
        self._root.bind("<Control-n>", lambda _: self._cmd_new_fieldday())
        self._root.bind("<Control-i>", lambda _: self._cmd_import_csv())

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label=t("menu_refresh"), command=self._cmd_refresh, accelerator="F5")
        menubar.add_cascade(label=t("menu_view"), menu=view_menu)
        self._root.bind("<F5>", lambda _: self._cmd_refresh())

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label=t("menu_manual_sync"), command=self._cmd_manual_sync, accelerator="Ctrl+R")
        tools_menu.add_command(label=t("menu_add_station"), command=self._cmd_add_station)
        tools_menu.add_separator()
        tools_menu.add_command(label=t("menu_settings"), command=self._cmd_settings)
        menubar.add_cascade(label=t("menu_tools"), menu=tools_menu)
        self._root.bind("<Control-r>", lambda _: self._cmd_manual_sync())

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="N1MM Setup…", command=lambda: show_help(self._root, HelpTopic.N1MM_SETUP))
        help_menu.add_command(label="CSV Import…", command=lambda: show_help(self._root, HelpTopic.CSV_IMPORT))
        help_menu.add_command(label="Matrix View…", command=lambda: show_help(self._root, HelpTopic.MATRIX_VIEW))
        help_menu.add_command(label="Manual Overrides…", command=lambda: show_help(self._root, HelpTopic.MANUAL_OVERRIDE))
        help_menu.add_command(label="Sync…", command=lambda: show_help(self._root, HelpTopic.SYNC))
        help_menu.add_separator()
        help_menu.add_command(label=t("menu_about"), command=self._show_about)
        menubar.add_cascade(label=t("menu_help"), menu=help_menu)
        self._root.config(menu=menubar)

    def _build_header(self) -> None:
        self._header = tk.Frame(self._root, bg="#1e3a5f", pady=8)
        self._header.pack(fill=tk.X)

        left = tk.Frame(self._header, bg="#1e3a5f")
        left.pack(side=tk.LEFT, padx=14)
        tk.Label(left, text=t("lbl_active_fieldday"), bg="#1e3a5f", fg="#aac4e0", font=("Segoe UI", 9)).pack(anchor=tk.W)
        self._lbl_fd_name = tk.Label(left, text="—", bg="#1e3a5f", fg="white", font=("Segoe UI", 13, "bold"))
        self._lbl_fd_name.pack(anchor=tk.W)

        right = tk.Frame(self._header, bg="#1e3a5f")
        right.pack(side=tk.RIGHT, padx=14)
        tk.Label(right, text=t("lbl_period"), bg="#1e3a5f", fg="#aac4e0", font=("Segoe UI", 9)).pack(anchor=tk.E)
        self._lbl_period = tk.Label(right, text="—", bg="#1e3a5f", fg="white", font=("Segoe UI", 10))
        self._lbl_period.pack(anchor=tk.E)

    def _refresh_header(self) -> None:
        fd = self._ctrl.fieldday
        if fd is None:
            self._lbl_fd_name.config(text="—")
            self._lbl_period.config(text="—")
            return
        self._lbl_fd_name.config(text=fd.name)
        if fd.start_utc and fd.end_utc:
            try:
                from datetime import datetime
                s = datetime.fromisoformat(fd.start_utc).strftime("%Y-%m-%d %H:%M UTC")
                e = datetime.fromisoformat(fd.end_utc).strftime("%Y-%m-%d %H:%M UTC")
                self._lbl_period.config(text=f"{s}  →  {e}")
            except ValueError:
                self._lbl_period.config(text=f"{fd.start_utc} → {fd.end_utc}")
        else:
            self._lbl_period.config(text="—")

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self._root, bg="#f0f0f0", pady=3, bd=1, relief=tk.GROOVE)
        bar.pack(fill=tk.X)
        btn = {"relief": tk.FLAT, "bg": "#f0f0f0", "font": ("Segoe UI", 9), "cursor": "hand2", "padx": 8}
        tk.Button(bar, text="⟳ " + t("btn_sync"), command=self._cmd_manual_sync, **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="📂 " + t("menu_import_csv"), command=self._cmd_import_csv, **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="➕ " + t("menu_add_station"), command=self._cmd_add_station, **btn).pack(side=tk.LEFT, padx=2)
        tk.Label(bar, text="|", bg="#f0f0f0", fg="#cccccc").pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="⚙ " + t("menu_settings"), command=self._cmd_settings, **btn).pack(side=tk.LEFT, padx=2)
        tk.Button(bar, text="? Help (F1)", command=lambda: show_help(self._root, HelpTopic.MAIN_WINDOW), **btn).pack(side=tk.RIGHT, padx=6)

    def _build_centre(self) -> None:
        self._centre = tk.Frame(self._root, bg="#f5f5f5")
        self._centre.pack(fill=tk.BOTH, expand=True)

    def _refresh_centre(self) -> None:
        for w in self._centre.winfo_children():
            w.destroy()
        if not self._ctrl.has_active_fieldday:
            self._show_no_fieldday_placeholder()
        else:
            self._show_matrix_view()

    def _show_no_fieldday_placeholder(self) -> None:
        wrapper = tk.Frame(self._centre, bg="#f5f5f5")
        wrapper.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        tk.Label(wrapper, text="📋", bg="#f5f5f5", font=("Segoe UI", 48)).pack()
        tk.Label(wrapper, text=t("no_active_fieldday"), bg="#f5f5f5", fg="#555555",
                 font=("Segoe UI", 12), wraplength=420, justify=tk.CENTER).pack(pady=(8, 16))
        tk.Label(wrapper, text=t("lbl_n1mm_setup_hint"), bg="#f5f5f5", fg="#888888",
                 font=("Segoe UI", 9), justify=tk.CENTER).pack()
        tk.Button(wrapper, text=t("menu_new_fieldday"), command=self._cmd_new_fieldday,
                  bg="#1e3a5f", fg="white", padx=12, pady=6, font=("Segoe UI", 10)).pack(pady=16)

    def _show_matrix_view(self) -> None:
        """Show the full interactive MatrixView."""
        from app.ui.matrix_view import MatrixView
        self._matrix_view = MatrixView(self._centre, self._ctrl)
        self._matrix_view.pack(fill=tk.BOTH, expand=True)

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self._root, bg="#e0e0e0", pady=3)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._lbl_connection = tk.Label(bar, text=t("status_waiting"),
                                        bg="#e0e0e0", fg="#666666",
                                        font=("Segoe UI", 9), anchor=tk.W)
        self._lbl_connection.pack(side=tk.LEFT, padx=8)
        tk.Label(bar, text="|", bg="#e0e0e0", fg="#aaaaaa").pack(side=tk.LEFT)
        self._lbl_last_rx = tk.Label(bar, text=f"{t('last_received')} {t('never')}",
                                     bg="#e0e0e0", fg="#888888", font=("Segoe UI", 9))
        self._lbl_last_rx.pack(side=tk.LEFT, padx=8)
        tk.Label(bar, text=t("app_subtitle"), bg="#e0e0e0", fg="#aaaaaa",
                 font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=8)
        self._schedule_status_refresh()

    def _schedule_status_refresh(self) -> None:
        self._update_status_bar()
        self._root.after(5000, self._schedule_status_refresh)

    def _update_status_bar(self) -> None:
        status = self._ctrl.listener_status
        if status is None:
            return
        color = _STATUS_COLORS.get(status, "#666666")
        label = {
            ListenerStatus.CONNECTED: t("status_connected"),
            ListenerStatus.WAITING:   t("status_waiting"),
            ListenerStatus.STALE:     t("status_stale"),
            ListenerStatus.ERROR:     t("status_error"),
        }.get(status, t("status_waiting"))
        self._lbl_connection.config(text=label, fg=color)
        self._lbl_last_rx.config(
            text=f"{t('last_received')} {self._ctrl.listener_last_received_str}"
        )

    def _on_matrix_changed(self) -> None:
        def _update():
            # If we have a live MatrixView, just refresh it (no rebuild)
            if (self._ctrl.has_active_fieldday
                    and hasattr(self, "_matrix_view")
                    and self._matrix_view is not None):
                try:
                    self._matrix_view.refresh()
                    return
                except tk.TclError:
                    pass
            self._refresh_centre()
        self._root.after(0, _update)

    def _on_status_changed(self, status, message) -> None:
        self._root.after(0, self._update_status_bar)

    def _on_fieldday_changed(self) -> None:
        self._root.after(0, self._refresh_header)
        self._root.after(0, self._refresh_centre)

    def _cmd_new_fieldday(self) -> None:
        from app.ui.fieldday_dialog import FieldDayDialog
        dlg = FieldDayDialog(self._root, settings=self._ctrl.settings)
        if dlg.result:
            try:
                self._ctrl.create_fieldday(dlg.result)
                messagebox.showinfo(t("dlg_new_fieldday_title"), t("msg_fieldday_saved"))
            except ValueError as exc:
                messagebox.showerror(t("dlg_new_fieldday_title"), str(exc))

    def _cmd_open_fieldday(self) -> None:
        names = self._ctrl.list_fielddays()
        if not names:
            messagebox.showinfo(t("menu_open_fieldday"), "No field days found. Create one first.")
            return
        self._cmd_switch_fieldday()

    def _cmd_switch_fieldday(self) -> None:
        names = self._ctrl.list_fielddays()
        if not names:
            messagebox.showinfo(t("menu_switch_fieldday"), "No field days found.")
            return
        win = tk.Toplevel(self._root)
        win.title(t("menu_switch_fieldday"))
        win.grab_set()
        win.resizable(False, False)
        tk.Label(win, text="Select a field day:", font=("Segoe UI", 10)).pack(padx=16, pady=(12, 4))
        lb = tk.Listbox(win, width=40, height=min(len(names), 12), font=("Segoe UI", 10))
        lb.pack(padx=16, pady=4)
        for name in names:
            lb.insert(tk.END, name)
        current = self._ctrl.fieldday
        if current and current.name in names:
            idx = names.index(current.name)
            lb.selection_set(idx)
            lb.see(idx)

        def _open():
            sel = lb.curselection()
            if not sel:
                return
            name = names[sel[0]]
            win.destroy()
            if not self._ctrl.open_fieldday(name):
                messagebox.showerror(t("menu_switch_fieldday"), f"Could not open: {name}")

        bf = tk.Frame(win)
        bf.pack(pady=(4, 12))
        tk.Button(bf, text=t("btn_ok"), command=_open, width=10,
                  bg="#1e3a5f", fg="white").pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text=t("btn_cancel"), command=win.destroy, width=10).pack(side=tk.LEFT, padx=4)
        lb.bind("<Double-Button-1>", lambda _: _open())
        win.update_idletasks()
        win.geometry(f"+{self._root.winfo_rootx()+100}+{self._root.winfo_rooty()+100}")

    def _cmd_edit_fieldday(self) -> None:
        if not self._ctrl.has_active_fieldday:
            messagebox.showinfo(t("menu_edit_fieldday"), t("no_active_fieldday"))
            return
        from app.ui.fieldday_dialog import FieldDayDialog
        dlg = FieldDayDialog(self._root, fieldday=self._ctrl.fieldday, settings=self._ctrl.settings)
        if dlg.result:
            self._ctrl.update_fieldday(dlg.result)
            messagebox.showinfo(t("menu_edit_fieldday"), t("msg_fieldday_saved"))

    def _cmd_import_csv(self) -> None:
        if not self._ctrl.has_active_fieldday:
            messagebox.showinfo(t("menu_import_csv"), t("no_active_fieldday"))
            return
        path = filedialog.askopenfilename(
            title=t("menu_import_csv"),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        result = self._ctrl.import_csv(Path(path))
        if not result.success:
            messagebox.showerror(t("menu_import_csv"),
                                 "\n".join(result.errors) or t("err_invalid_csv"))
            return
        if result.removed_callsigns:
            if messagebox.askyesno(t("menu_import_csv"),
                t("msg_confirm_delete_stations", count=len(result.removed_callsigns))
                + f"\n\n{', '.join(result.removed_callsigns)}"):
                self._ctrl.apply_csv_removals(result.removed_callsigns)
        messagebox.showinfo(t("menu_import_csv"),
            t("msg_import_success", count=len(result.stations))
            + f"\nAdded: {len(result.added)}, Updated: {len(result.updated)}"
            + f"\nInvalid: {len(result.skipped_invalid)}")

    def _cmd_export_csv(self) -> None:
        if not self._ctrl.has_active_fieldday:
            messagebox.showinfo(t("menu_export_csv"), t("no_active_fieldday"))
            return
        messagebox.showinfo(t("menu_export_csv"), "CSV export — implemented in Step 11.")

    def _cmd_export_pdf(self) -> None:
        if not self._ctrl.has_active_fieldday:
            messagebox.showinfo(t("menu_export_pdf"), t("no_active_fieldday"))
            return
        messagebox.showinfo(t("menu_export_pdf"), "PDF export — implemented in Step 11.")

    def _cmd_refresh(self) -> None:
        self._refresh_centre()

    def _cmd_manual_sync(self) -> None:
        if not self._ctrl.has_active_fieldday:
            messagebox.showinfo(t("menu_manual_sync"), t("no_active_fieldday"))
            return
        result = self._ctrl.recalculate()
        messagebox.showinfo(t("menu_manual_sync"),
            t("msg_sync_complete",
              worked=result.worked_combinations,
              unworked=result.unworked_combinations,
              excluded=result.excluded_count))

    def _cmd_add_station(self) -> None:
        if not self._ctrl.has_active_fieldday:
            messagebox.showinfo(t("menu_add_station"), t("no_active_fieldday"))
            return
        win = tk.Toplevel(self._root)
        win.title(t("menu_add_station"))
        win.grab_set()
        win.resizable(False, False)
        bind_f1(win, HelpTopic.MANUAL_STATION)
        pad = {"padx": 10, "pady": 5}
        vars_ = {}
        for row, (key, label) in enumerate([
            ("call", "Callsign *"), ("name", "Name"),
            ("club", "Club"), ("remarks", "Remarks"),
        ]):
            tk.Label(win, text=label, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, **pad)
            v = tk.StringVar()
            vars_[key] = v
            ttk.Entry(win, textvariable=v, width=30).grid(row=row, column=1, sticky=tk.W, **pad)

        def _save():
            from app.core.models import Station
            from app.core.callsign import is_valid_callsign
            call = vars_["call"].get().strip()
            if not is_valid_callsign(call):
                messagebox.showerror(t("menu_add_station"), f"Invalid callsign: {call!r}")
                return
            s = Station(callsign=call, normalized_callsign=call.upper(),
                        name=vars_["name"].get().strip(),
                        club=vars_["club"].get().strip(),
                        remarks=vars_["remarks"].get().strip(),
                        source="manual")
            if self._ctrl.add_station_manual(s):
                win.destroy()
                messagebox.showinfo(t("menu_add_station"), f"Station {call} added.")
            else:
                messagebox.showwarning(t("menu_add_station"), f"Station {call} already exists.")

        bf = tk.Frame(win)
        bf.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(bf, text=t("btn_add"), command=_save, width=10,
                  bg="#1e3a5f", fg="white").pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text=t("btn_cancel"), command=win.destroy, width=10).pack(side=tk.LEFT, padx=4)

    def _cmd_settings(self) -> None:
        messagebox.showinfo(t("menu_settings"), "Full settings dialog — implemented in Step 9.")

    def _show_about(self) -> None:
        messagebox.showinfo(t("dlg_about_title"), t("dlg_about_text"))

    def _on_quit(self) -> None:
        self._ctrl.shutdown()
        self._root.destroy()
