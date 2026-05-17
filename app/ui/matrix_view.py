"""
app/ui/matrix_view.py
=====================
Interactive Station × Band matrix for N1MM Field Day Tracker.

Design principles
-----------------
The operator is busy.  This view must answer ONE question instantly:
"Which station do I need to work next, and on which band?"

Layout decisions
----------------
- Default filter: "Open" — only stations with ≥1 unworked band.
  Fully worked stations disappear automatically.
- Sort order: stations with MOST open bands at the top (highest need).
- Cell size: large enough to click easily, small enough to see many stations.
- Colours: strong contrast; green = done, white = open (the operator's goal).
- Station column: callsign (bold) + name + club on two lines.
- Right-click any cell → manual override menu.
- Hover → tooltip with timestamp / mode / frequency details.
- Live search box filters by callsign (no Enter needed).
- Keyboard: arrow keys navigate cells; Enter/Space opens context menu.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from app.core.status import Status, DEFAULT_STATUS_COLORS, STATUS_SYMBOLS
from app.i18n.translations import t
from app.ui.help_system import HelpTopic, show_help

if TYPE_CHECKING:
    from app.app_controller import AppController

log = logging.getLogger(__name__)

# ── Cell / column dimensions ─────────────────────────────────────────────────
CELL_W   = 64     # band column width  (px)
CELL_H   = 42     # cell height        (px)
STATION_W = 170   # station name column width (px)
NAME_W    = 120   # operator name sub-column  (px)
HEADER_H  = 36    # band header height (px)

# ── Colours ──────────────────────────────────────────────────────────────────
ROW_BG_ODD  = "#ffffff"
ROW_BG_EVEN = "#f4f6f8"
ROW_HOVER   = "#e3f2fd"
HDR_BG      = "#1e3a5f"
HDR_FG      = "#ffffff"
STATION_FG  = "#1a237e"
NAME_FG     = "#546e7a"
WORKED_FG   = "#ffffff"
WORKED_SYMBOL_FONT = ("Segoe UI", 12, "bold")
CELL_FONT          = ("Segoe UI", 11)
STATION_FONT       = ("Segoe UI", 10, "bold")
NAME_FONT          = ("Segoe UI", 8)

# ── Filter constants ──────────────────────────────────────────────────────────
FILTER_OPEN    = "open"       # ≥1 band not worked  (DEFAULT)
FILTER_ALL     = "all"
FILTER_PARTIAL = "partial"    # ≥1 worked, ≥1 not worked
FILTER_FULL    = "full"       # all selected bands worked
FILTER_NONE    = "none_worked"# zero bands worked


class MatrixView(tk.Frame):
    """Full Station × Band matrix widget.

    Drop this into any Tkinter container.  Call :meth:`refresh` whenever
    the controller data changes.

    Parameters
    ----------
    parent:
        Tkinter parent widget.
    controller:
        Live :class:`~app.app_controller.AppController` instance.
    """

    def __init__(self, parent: tk.Widget, controller: "AppController") -> None:
        super().__init__(parent, bg="#f5f5f5")
        self._ctrl = controller
        self._filter  = FILTER_OPEN       # default: show only open stations
        self._search  = ""
        self._band_filter = "all"
        self._sort_col    = None          # None = by open-band count desc
        self._sort_rev    = False
        self._hover_row   = None
        self._selected_cell: tuple | None = None  # (norm_call, band)
        self._tooltip_win  = None
        self._tooltip_job  = None

        # Rows built in _build_body; keyed by normalized_callsign
        self._row_frames: dict[str, tk.Frame] = {}
        self._cell_labels: dict[tuple, tk.Label] = {}   # (call, band) → Label

        self._build_toolbar()
        self._build_progress_bar()
        self._build_matrix()
        self.refresh()

    # =========================================================================
    # Public interface
    # =========================================================================

    def refresh(self) -> None:
        """Re-render the matrix from current controller state."""
        self._rebuild_rows()
        self._update_progress()

    # =========================================================================
    # Toolbar
    # =========================================================================

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, bg="#eceff1", pady=6)
        bar.pack(fill=tk.X, padx=0)

        # ── Search ──────────────────────────────────────────────────────────
        tk.Label(bar, text=t("lbl_search"), bg="#eceff1",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search_change())
        search_entry = ttk.Entry(bar, textvariable=self._search_var, width=16)
        search_entry.pack(side=tk.LEFT, padx=(0, 8))
        search_entry.bind("<Escape>", lambda _: self._search_var.set(""))

        # Clear button
        tk.Button(bar, text="✕", relief=tk.FLAT, bg="#eceff1",
                  font=("Segoe UI", 8), cursor="hand2",
                  command=lambda: self._search_var.set("")).pack(side=tk.LEFT, padx=(0, 14))

        # ── Filter tabs ──────────────────────────────────────────────────────
        tk.Label(bar, text="Filter:", bg="#eceff1",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))

        self._filter_btns: dict[str, tk.Button] = {}
        filters = [
            (FILTER_OPEN,    "⚡ Open",       "#e53935", "#ffffff"),  # red = urgent
            (FILTER_ALL,     "All",            "#455a64", "#ffffff"),
            (FILTER_NONE,    "Not started",    "#546e7a", "#ffffff"),
            (FILTER_PARTIAL, "Partial",        "#ef6c00", "#ffffff"),
            (FILTER_FULL,    "✓ Complete",     "#2e7d32", "#ffffff"),
        ]
        for key, label, _active_bg, _active_fg in filters:
            btn = tk.Button(
                bar, text=label,
                relief=tk.FLAT,
                font=("Segoe UI", 9),
                padx=8, pady=2,
                cursor="hand2",
                command=lambda k=key: self._set_filter(k),
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._filter_btns[key] = btn

        self._update_filter_buttons()

        # ── Band filter ──────────────────────────────────────────────────────
        tk.Label(bar, text=t("lbl_band_filter"), bg="#eceff1",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(16, 2))
        self._band_var = tk.StringVar(value="All")
        self._band_combo = ttk.Combobox(
            bar, textvariable=self._band_var, width=8,
            state="readonly",
        )
        self._band_combo.pack(side=tk.LEFT, padx=(0, 8))
        self._band_combo.bind("<<ComboboxSelected>>", lambda _: self._on_band_filter())

        # ── Sort ─────────────────────────────────────────────────────────────
        tk.Label(bar, text="Sort:", bg="#eceff1",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 2))
        self._sort_var = tk.StringVar(value="Open bands ↓")
        sort_combo = ttk.Combobox(
            bar, textvariable=self._sort_var, width=14,
            state="readonly",
            values=["Open bands ↓", "Callsign A→Z", "Callsign Z→A",
                    "Name A→Z", "% worked ↓"],
        )
        sort_combo.pack(side=tk.LEFT)
        sort_combo.bind("<<ComboboxSelected>>", lambda _: self._on_sort_change())

        # ── Help ─────────────────────────────────────────────────────────────
        tk.Button(bar, text="?", relief=tk.FLAT, bg="#eceff1",
                  font=("Segoe UI", 9, "bold"), fg="#1e3a5f",
                  cursor="question_arrow",
                  command=lambda: show_help(self, HelpTopic.MATRIX_VIEW),
                  ).pack(side=tk.RIGHT, padx=8)

    # =========================================================================
    # Progress bar
    # =========================================================================

    def _build_progress_bar(self) -> None:
        self._progress_frame = tk.Frame(self, bg="#e8eaf6", pady=5)
        self._progress_frame.pack(fill=tk.X)

        # Stat labels
        stats_frame = tk.Frame(self._progress_frame, bg="#e8eaf6")
        stats_frame.pack(side=tk.LEFT, padx=14)

        self._stat_labels: dict[str, tk.Label] = {}
        for key, label, color in [
            ("open",    "Open",     "#c62828"),
            ("partial", "Partial",  "#ef6c00"),
            ("done",    "Complete", "#2e7d32"),
            ("total",   "Total",    "#1e3a5f"),
        ]:
            f = tk.Frame(stats_frame, bg="#e8eaf6")
            f.pack(side=tk.LEFT, padx=14)
            v = tk.Label(f, text="0", bg="#e8eaf6",
                         font=("Segoe UI", 20, "bold"), fg=color)
            v.pack()
            tk.Label(f, text=label, bg="#e8eaf6",
                     font=("Segoe UI", 8), fg="#555").pack()
            self._stat_labels[key] = v

        # Progress canvas
        self._prog_canvas = tk.Canvas(
            self._progress_frame, height=16,
            bg="#e0e0e0", highlightthickness=0,
        )
        self._prog_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True,
                                padx=(0, 14), pady=4)

    def _update_progress(self) -> None:
        fd = self._ctrl.fieldday
        if fd is None:
            return
        stations = self._ctrl.stations
        matrix   = self._ctrl.matrix
        bands    = fd.selected_bands
        n_bands  = len(bands)

        total = len(stations)
        done = partial = open_ = 0
        for s in stations:
            nc = s.normalized_callsign
            worked = sum(
                1 for b in bands
                if matrix.get((nc, b)) and matrix[(nc, b)].status.is_worked()
            )
            excluded = sum(
                1 for b in bands
                if matrix.get((nc, b)) and matrix[(nc, b)].status.is_excluded()
            )
            active = n_bands - excluded
            if active == 0:
                continue
            if worked == active:
                done += 1
            elif worked > 0:
                partial += 1
            else:
                open_ += 1

        self._stat_labels["open"].config(text=str(open_))
        self._stat_labels["partial"].config(text=str(partial))
        self._stat_labels["done"].config(text=str(done))
        self._stat_labels["total"].config(text=str(total))

        # Draw progress bar
        self._prog_canvas.update_idletasks()
        w = self._prog_canvas.winfo_width() or 300
        self._prog_canvas.delete("all")
        if total == 0:
            return
        x_done    = int(w * done / total)
        x_partial = int(w * (done + partial) / total)
        if x_done > 0:
            self._prog_canvas.create_rectangle(0, 0, x_done, 16,
                                               fill="#43a047", outline="")
        if x_partial > x_done:
            self._prog_canvas.create_rectangle(x_done, 0, x_partial, 16,
                                               fill="#ef6c00", outline="")
        if x_partial < w:
            self._prog_canvas.create_rectangle(x_partial, 0, w, 16,
                                               fill="#e57373", outline="")
        pct = int(100 * (done + partial * 0.5) / total) if total else 0
        self._prog_canvas.create_text(
            w // 2, 8, text=f"{done}/{total} complete ({pct}%)",
            fill="white", font=("Segoe UI", 8, "bold"),
        )

    # =========================================================================
    # Matrix area
    # =========================================================================

    def _build_matrix(self) -> None:
        """Build the scrollable matrix area with sticky header."""
        self._matrix_outer = tk.Frame(self, bg="#f5f5f5")
        self._matrix_outer.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        self._vscroll = ttk.Scrollbar(self._matrix_outer, orient=tk.VERTICAL)
        self._vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._hscroll = ttk.Scrollbar(self._matrix_outer, orient=tk.HORIZONTAL)
        self._hscroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Canvas (scrollable body)
        self._canvas = tk.Canvas(
            self._matrix_outer, bg="#f5f5f5",
            highlightthickness=0,
            yscrollcommand=self._vscroll.set,
            xscrollcommand=self._hscroll.set,
        )
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._vscroll.config(command=self._canvas.yview)
        self._hscroll.config(command=self._canvas.xview)

        # Inner frame inside canvas (all rows go here)
        self._body = tk.Frame(self._canvas, bg="#f5f5f5")
        self._body_window = self._canvas.create_window(
            (0, 0), window=self._body, anchor=tk.NW
        )

        self._body.bind("<Configure>", self._on_body_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel
        self._canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"
            ),
        )
        # Shift+scroll → horizontal
        self._canvas.bind_all(
            "<Shift-MouseWheel>",
            lambda e: self._canvas.xview_scroll(
                int(-1 * (e.delta / 120)), "units"
            ),
        )

    def _on_body_configure(self, _event=None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig(self._body_window, width=event.width)

    # =========================================================================
    # Row building
    # =========================================================================

    def _get_filtered_sorted_stations(self):
        fd = self._ctrl.fieldday
        if fd is None:
            return []

        stations = self._ctrl.stations
        matrix   = self._ctrl.matrix
        bands    = fd.selected_bands
        search   = self._search.lower()

        def _open_count(s):
            return sum(
                1 for b in bands
                if not matrix.get((s.normalized_callsign, b))
                or matrix[(s.normalized_callsign, b)].status
                   in (Status.NOT_WORKED, Status.MANUAL_NOT_WORKED)
            )

        def _worked_count(s):
            return sum(
                1 for b in bands
                if matrix.get((s.normalized_callsign, b))
                and matrix[(s.normalized_callsign, b)].status.is_worked()
            )

        def _excluded_count(s):
            return sum(
                1 for b in bands
                if matrix.get((s.normalized_callsign, b))
                and matrix[(s.normalized_callsign, b)].status.is_excluded()
            )

        result = []
        for s in stations:
            nc = s.normalized_callsign

            # Search filter
            if search and search not in nc.lower() \
                    and search not in (s.name or "").lower() \
                    and search not in (s.club or "").lower():
                continue

            worked   = _worked_count(s)
            excluded = _excluded_count(s)
            active   = len(bands) - excluded
            open_    = max(0, active - worked)
            is_full  = (active > 0 and worked >= active)
            is_part  = (worked > 0 and open_ > 0)
            is_none  = (worked == 0 and open_ > 0)

            # Status filter
            if self._filter == FILTER_OPEN and open_ == 0 and not is_none:
                # Fully worked or all-excluded → skip
                if is_full or active == 0:
                    continue
            elif self._filter == FILTER_FULL and not is_full:
                continue
            elif self._filter == FILTER_PARTIAL and not is_part:
                continue
            elif self._filter == FILTER_NONE and not is_none:
                continue

            result.append((s, worked, open_, excluded))

        # Sort
        sort = self._sort_var.get() if hasattr(self, "_sort_var") else "Open bands ↓"
        if sort == "Open bands ↓":
            result.sort(key=lambda x: (-x[2], x[0].normalized_callsign))
        elif sort == "Callsign A→Z":
            result.sort(key=lambda x: x[0].normalized_callsign)
        elif sort == "Callsign Z→A":
            result.sort(key=lambda x: x[0].normalized_callsign, reverse=True)
        elif sort == "Name A→Z":
            result.sort(key=lambda x: x[0].name.lower())
        elif sort == "% worked ↓":
            result.sort(key=lambda x: -x[1])

        return result

    def _rebuild_rows(self) -> None:
        """Destroy and rebuild all matrix rows."""
        fd = self._ctrl.fieldday
        if fd is None:
            for w in self._body.winfo_children():
                w.destroy()
            self._row_frames.clear()
            self._cell_labels.clear()
            self._update_band_combo([])
            return

        bands = fd.selected_bands
        self._update_band_combo(bands)

        # Destroy existing
        for w in self._body.winfo_children():
            w.destroy()
        self._row_frames.clear()
        self._cell_labels.clear()

        # ── Sticky header row ─────────────────────────────────────────────
        hdr = tk.Frame(self._body, bg=HDR_BG)
        hdr.pack(fill=tk.X, side=tk.TOP)

        # Station column header
        tk.Label(
            hdr, text="Station", bg=HDR_BG, fg=HDR_FG,
            width=20, anchor=tk.W,
            font=("Segoe UI", 9, "bold"), pady=6,
        ).pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(
            hdr, text="Name / Club", bg=HDR_BG, fg=HDR_FG,
            width=14, anchor=tk.W,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)

        tk.Label(
            hdr, text="Rmk", bg=HDR_BG, fg=HDR_FG,
            width=4, anchor=tk.W,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)

        # Band headers
        for band in bands:
            lbl = tk.Label(
                hdr, text=band.upper(), bg=HDR_BG, fg=HDR_FG,
                width=7, anchor=tk.CENTER,
                font=("Segoe UI", 9, "bold"),
                relief=tk.GROOVE, bd=1,
            )
            lbl.pack(side=tk.LEFT, padx=1, pady=2)

        # ── Station rows ──────────────────────────────────────────────────
        filtered = self._get_filtered_sorted_stations()
        matrix   = self._ctrl.matrix

        if not filtered:
            empty_lbl = tk.Label(
                self._body,
                text="No stations match the current filter.",
                bg="#f5f5f5", fg="#888", font=("Segoe UI", 10),
                pady=20,
            )
            empty_lbl.pack()
            return

        for idx, (station, worked, open_, excluded) in enumerate(filtered):
            nc    = station.normalized_callsign
            row_bg = ROW_BG_ODD if idx % 2 == 0 else ROW_BG_EVEN

            row = tk.Frame(self._body, bg=row_bg, pady=1)
            row.pack(fill=tk.X, side=tk.TOP)
            self._row_frames[nc] = row

            # ── Station name cell ─────────────────────────────────────────
            name_frame = tk.Frame(row, bg=row_bg, width=STATION_W)
            name_frame.pack(side=tk.LEFT, padx=(4, 0))
            name_frame.pack_propagate(False)

            tk.Label(
                name_frame, text=nc, bg=row_bg,
                fg=STATION_FG, anchor=tk.W,
                font=STATION_FONT,
            ).pack(anchor=tk.W, pady=(4, 0))

            sub_text = " / ".join(x for x in [station.name, station.club] if x)
            if sub_text:
                tk.Label(
                    name_frame, text=sub_text, bg=row_bg,
                    fg=NAME_FG, anchor=tk.W,
                    font=NAME_FONT,
                ).pack(anchor=tk.W)

            # ── Remarks badge ─────────────────────────────────────────────
            rmk_frame = tk.Frame(row, bg=row_bg, width=36)
            rmk_frame.pack(side=tk.LEFT, padx=2)
            rmk_frame.pack_propagate(False)

            if station.remarks:
                rmk_lbl = tk.Label(
                    rmk_frame, text="💬", bg=row_bg,
                    font=("Segoe UI", 9), cursor="hand2",
                )
                rmk_lbl.pack(anchor=tk.CENTER, pady=4)
                rmk_lbl.bind("<Button-1>",
                             lambda e, s=station: self._show_remarks(e, s))
                self._bind_tooltip(rmk_lbl, station.remarks)

            # ── Band cells ────────────────────────────────────────────────
            for band in bands:
                # Apply band filter
                if self._band_filter != "all" and band != self._band_filter:
                    # Show as dimmed placeholder
                    tk.Frame(row, bg=row_bg, width=CELL_W + 2,
                             height=CELL_H).pack(side=tk.LEFT, padx=1)
                    continue

                key = (nc, band)
                cell = matrix.get(key)
                status_val = cell.status.value if cell else Status.NOT_WORKED.value

                cell_bg  = self._ctrl.settings.status_colors.get(
                    status_val, DEFAULT_STATUS_COLORS.get(status_val, "#FFFFFF")
                )
                symbol   = STATUS_SYMBOLS.get(status_val, "")

                # Make worked cells extra visible
                if status_val in (Status.WORKED_BY_N1MM.value,
                                  Status.MANUAL_WORKED.value):
                    sym_font = WORKED_SYMBOL_FONT
                    sym_fg   = WORKED_FG
                elif status_val == Status.NOT_WORKED.value:
                    sym_font = ("Segoe UI", 10)
                    sym_fg   = "#cccccc"
                else:
                    sym_font = CELL_FONT
                    sym_fg   = "#333333"

                cell_lbl = tk.Label(
                    row,
                    text=symbol,
                    bg=cell_bg,
                    fg=sym_fg,
                    font=sym_font,
                    width=7, height=2,
                    relief=tk.GROOVE,
                    bd=1,
                    cursor="hand2",
                )
                cell_lbl.pack(side=tk.LEFT, padx=1, pady=1)
                self._cell_labels[key] = cell_lbl

                # Bindings
                cell_lbl.bind("<Button-3>",
                    lambda e, k=key: self._show_context_menu(e, k))
                cell_lbl.bind("<Button-1>",
                    lambda e, k=key: self._on_cell_click(e, k))
                cell_lbl.bind("<Enter>",
                    lambda e, k=key, r=row, bg=row_bg:
                        self._on_cell_enter(e, k, r, bg))
                cell_lbl.bind("<Leave>",
                    lambda e, k=key, r=row, bg=row_bg:
                        self._on_cell_leave(e, k, r, bg))

                # Tooltip
                tooltip_text = self._build_tooltip_text(nc, band, cell)
                self._bind_tooltip(cell_lbl, tooltip_text)

            # ── Row hover ─────────────────────────────────────────────────
            row.bind("<Enter>",
                lambda e, r=row, bg=row_bg:
                    self._on_row_enter(r, bg))
            row.bind("<Leave>",
                lambda e, r=row, bg=row_bg:
                    self._on_row_leave(r, bg))
            name_frame.bind("<Enter>",
                lambda e, r=row, bg=row_bg: self._on_row_enter(r, bg))
            name_frame.bind("<Leave>",
                lambda e, r=row, bg=row_bg: self._on_row_leave(r, bg))

        self._on_body_configure()

    # =========================================================================
    # Cell interaction
    # =========================================================================

    def _on_cell_click(self, event, key: tuple) -> None:
        """Left-click: select cell (prepare for keyboard actions)."""
        self._selected_cell = key

    def _on_cell_enter(self, event, key, row, orig_bg) -> None:
        lbl = self._cell_labels.get(key)
        if lbl:
            # Lighten the cell slightly
            cur_bg = lbl.cget("bg")
            if cur_bg == "#FFFFFF":
                lbl.config(bg="#e3f2fd")

    def _on_cell_leave(self, event, key, row, orig_bg) -> None:
        lbl = self._cell_labels.get(key)
        if lbl:
            nc, band = key
            matrix = self._ctrl.matrix
            cell = matrix.get(key)
            status_val = cell.status.value if cell else Status.NOT_WORKED.value
            cell_bg = self._ctrl.settings.status_colors.get(
                status_val, DEFAULT_STATUS_COLORS.get(status_val, "#FFFFFF")
            )
            lbl.config(bg=cell_bg)

    def _on_row_enter(self, row, orig_bg) -> None:
        for child in row.winfo_children():
            try:
                child.config(bg=ROW_HOVER)
                for sub in child.winfo_children():
                    try:
                        if sub.cget("bg") in (orig_bg, ROW_BG_ODD, ROW_BG_EVEN):
                            sub.config(bg=ROW_HOVER)
                    except tk.TclError:
                        pass
            except tk.TclError:
                pass

    def _on_row_leave(self, row, orig_bg) -> None:
        for child in row.winfo_children():
            try:
                child.config(bg=orig_bg)
                for sub in child.winfo_children():
                    try:
                        if sub.cget("bg") == ROW_HOVER:
                            sub.config(bg=orig_bg)
                    except tk.TclError:
                        pass
            except tk.TclError:
                pass

    # =========================================================================
    # Context menu (right-click)
    # =========================================================================

    def _show_context_menu(self, event, key: tuple) -> None:
        nc, band = key
        matrix = self._ctrl.matrix
        cell   = matrix.get(key)
        status = cell.status if cell else Status.NOT_WORKED

        menu = tk.Menu(self, tearoff=False)
        menu.add_command(
            label=f"  {nc}  +  {band.upper()}",
            state=tk.DISABLED,
            font=("Segoe UI", 9, "bold"),
        )
        menu.add_separator()

        # Current status
        status_name = {
            Status.NOT_WORKED:        t("status_not_worked"),
            Status.WORKED_BY_N1MM:    t("status_worked_n1mm"),
            Status.MANUAL_WORKED:     t("status_manual_worked"),
            Status.MANUAL_NOT_WORKED: t("status_manual_not_worked"),
            Status.EXCLUDED:          t("status_excluded"),
        }.get(status, status.value)

        menu.add_command(
            label=f"  Current: {status_name}",
            state=tk.DISABLED,
            font=("Segoe UI", 8),
        )
        menu.add_separator()

        # Override actions
        menu.add_command(
            label="✓  " + t("override_mark_worked"),
            command=lambda: self._apply_override(nc, band, Status.MANUAL_WORKED),
        )
        menu.add_command(
            label="✗  " + t("override_mark_not_worked"),
            command=lambda: self._apply_override(nc, band, Status.MANUAL_NOT_WORKED),
        )
        menu.add_command(
            label="—  " + t("override_exclude"),
            command=lambda: self._apply_override(nc, band, Status.EXCLUDED),
        )

        if cell and cell.has_override:
            menu.add_separator()
            menu.add_command(
                label="↺  " + t("override_clear"),
                command=lambda: self._clear_override(nc, band),
                font=("Segoe UI", 9, "bold"),
            )

        menu.add_separator()
        menu.add_command(
            label="💬  Edit Remarks…",
            command=lambda: self._edit_remarks_for(nc),
        )

        menu.tk_popup(event.x_root, event.y_root)

    def _apply_override(self, nc: str, band: str, status: Status) -> None:
        self._ctrl.set_override(nc, band, status)
        # refresh is triggered via controller callback

    def _clear_override(self, nc: str, band: str) -> None:
        self._ctrl.clear_override(nc, band)

    def _edit_remarks_for(self, nc: str) -> None:
        station = next(
            (s for s in self._ctrl.stations if s.normalized_callsign == nc),
            None,
        )
        if station is None:
            return

        win = tk.Toplevel(self)
        win.title(f"Remarks — {nc}")
        win.grab_set()
        win.resizable(False, False)

        tk.Label(win, text=f"Remarks for {nc}:",
                 font=("Segoe UI", 10, "bold")).pack(padx=12, pady=(10, 4), anchor=tk.W)

        txt = tk.Text(win, width=40, height=4, font=("Segoe UI", 10),
                      wrap=tk.WORD)
        txt.pack(padx=12, pady=4)
        txt.insert("1.0", station.remarks or "")

        def _save():
            new_remarks = txt.get("1.0", tk.END).strip()
            self._ctrl.update_station_remarks(nc, new_remarks)
            win.destroy()
            self.refresh()

        bf = tk.Frame(win)
        bf.pack(pady=(4, 10))
        tk.Button(bf, text=t("btn_save"), command=_save, width=10,
                  bg="#1e3a5f", fg="white").pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text=t("btn_cancel"), command=win.destroy,
                  width=10).pack(side=tk.LEFT, padx=4)

    def _show_remarks(self, event, station) -> None:
        """Show full remarks for a station on click."""
        messagebox.showinfo(
            f"Remarks — {station.normalized_callsign}",
            station.remarks or "(no remarks)",
        )

    # =========================================================================
    # Tooltip
    # =========================================================================

    def _build_tooltip_text(self, nc: str, band: str, cell) -> str:
        if cell is None:
            return f"{nc} + {band}\nStatus: Not worked"

        lines = [f"{nc} + {band.upper()}"]

        status_name = {
            Status.NOT_WORKED:        t("status_not_worked"),
            Status.WORKED_BY_N1MM:    t("status_worked_n1mm"),
            Status.MANUAL_WORKED:     t("status_manual_worked"),
            Status.MANUAL_NOT_WORKED: t("status_manual_not_worked"),
            Status.EXCLUDED:          t("status_excluded"),
        }.get(cell.status, cell.status.value)

        lines.append(f"Status: {status_name}")
        if cell.has_override:
            lines.append("⚠ Manual override active")
        if cell.worked_timestamp_utc:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(cell.worked_timestamp_utc)
                lines.append(f"Worked: {dt.strftime('%Y-%m-%d %H:%M UTC')}")
            except ValueError:
                lines.append(f"Worked: {cell.worked_timestamp_utc}")
        if cell.mode:
            lines.append(f"Mode: {cell.mode}")
        if cell.frequency_hz:
            mhz = cell.frequency_hz / 1_000_000
            lines.append(f"Freq: {mhz:.3f} MHz")

        return "\n".join(lines)

    def _bind_tooltip(self, widget: tk.Widget, text: str) -> None:
        widget.bind("<Enter>",
            lambda e, t=text: self._schedule_tooltip(e, t), add="+")
        widget.bind("<Leave>", lambda e: self._cancel_tooltip(), add="+")

    def _schedule_tooltip(self, event, text: str) -> None:
        self._cancel_tooltip()
        self._tooltip_job = self.after(
            600, lambda: self._show_tooltip(event, text)
        )

    def _cancel_tooltip(self) -> None:
        if self._tooltip_job:
            self.after_cancel(self._tooltip_job)
            self._tooltip_job = None
        if self._tooltip_win:
            try:
                self._tooltip_win.destroy()
            except tk.TclError:
                pass
            self._tooltip_win = None

    def _show_tooltip(self, event, text: str) -> None:
        x = event.widget.winfo_rootx() + 20
        y = event.widget.winfo_rooty() + event.widget.winfo_height() + 4

        self._tooltip_win = tk.Toplevel(self)
        self._tooltip_win.wm_overrideredirect(True)
        self._tooltip_win.wm_geometry(f"+{x}+{y}")

        bg = "#fffde7"
        frame = tk.Frame(self._tooltip_win, bg=bg,
                         relief=tk.SOLID, bd=1)
        frame.pack()
        tk.Label(frame, text=text, bg=bg, justify=tk.LEFT,
                 font=("Segoe UI", 9), padx=8, pady=4).pack()

    # =========================================================================
    # Filter / search / sort
    # =========================================================================

    def _set_filter(self, filter_key: str) -> None:
        self._filter = filter_key
        self._update_filter_buttons()
        self._rebuild_rows()

    def _update_filter_buttons(self) -> None:
        styles = {
            FILTER_OPEN:    ("#e53935", "#ffffff"),
            FILTER_ALL:     ("#455a64", "#ffffff"),
            FILTER_NONE:    ("#546e7a", "#ffffff"),
            FILTER_PARTIAL: ("#ef6c00", "#ffffff"),
            FILTER_FULL:    ("#2e7d32", "#ffffff"),
        }
        for key, btn in self._filter_btns.items():
            if key == self._filter:
                bg, fg = styles.get(key, ("#1e3a5f", "#ffffff"))
                btn.config(bg=bg, fg=fg,
                           relief=tk.SUNKEN, font=("Segoe UI", 9, "bold"))
            else:
                btn.config(bg="#eceff1", fg="#333333",
                           relief=tk.FLAT, font=("Segoe UI", 9))

    def _on_search_change(self) -> None:
        self._search = self._search_var.get()
        self._rebuild_rows()

    def _on_band_filter(self) -> None:
        val = self._band_var.get()
        self._band_filter = "all" if val == "All" else val.lower()
        self._rebuild_rows()

    def _on_sort_change(self) -> None:
        self._rebuild_rows()

    def _update_band_combo(self, bands: list[str]) -> None:
        values = ["All"] + [b.upper() for b in bands]
        self._band_combo.config(values=values)
        if self._band_var.get() not in values:
            self._band_var.set("All")
            self._band_filter = "all"
