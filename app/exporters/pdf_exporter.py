"""
app/exporters/pdf_exporter.py
==============================
PDF report exporter for N1MM Field Day Tracker.

Generates a professional, print-ready PDF report containing:
  - Title page with field day details
  - Summary statistics with progress bar
  - Legend (colour key)
  - Full station × band matrix

Uses reportlab (pure Python, no external tools required).

Public API
----------
PDFExporter.export(path, fieldday, stations, matrix, settings)
    → ExportResult
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.band_plan import ordered_band_names
from app.core.models import AppSettings, FieldDay, Station, StationBandStatus
from app.core.status import DEFAULT_STATUS_COLORS, STATUS_SYMBOLS, Status
from app.storage.json_store import ensure_dir

log = logging.getLogger(__name__)

# ── Colours used in the report ────────────────────────────────────────────────
NAVY   = colors.HexColor("#1e3a5f")
WHITE  = colors.white
LIGHT  = colors.HexColor("#e8eaf6")
GREY   = colors.HexColor("#f5f5f5")
BLACK  = colors.black

# Cell size in points (1 mm = 2.835 pt)
CELL_W_PT = 14 * mm
CELL_H_PT = 7  * mm


@dataclass
class ExportResult:
    """Result of an export operation."""
    path: Path
    success: bool
    pages: int = 0
    error: str = ""


def _hex_to_color(hex_str: str) -> colors.Color:
    """Convert a #RRGGBB hex string to a reportlab Color."""
    try:
        h = hex_str.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return colors.Color(r / 255, g / 255, b / 255)
    except (ValueError, IndexError):
        return WHITE


def _text_color_for_bg(hex_bg: str) -> colors.Color:
    """Return black or white depending on background luminance."""
    try:
        h = hex_bg.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return BLACK if lum > 140 else WHITE
    except (ValueError, IndexError):
        return BLACK


class PDFExporter:
    """Stateless PDF report generator."""

    @staticmethod
    def export(
        path: Path,
        fieldday: FieldDay,
        stations: list[Station],
        matrix: dict[tuple[str, str], StationBandStatus],
        settings: AppSettings | None = None,
    ) -> ExportResult:
        """Generate the PDF report.

        Parameters
        ----------
        path:
            Destination file path.
        fieldday:
            Active field day.
        stations:
            All participating stations.
        matrix:
            Computed station × band matrix.
        settings:
            App settings (used for custom status colours).
        """
        path = Path(path)
        ensure_dir(path.parent)

        # Resolve effective colours
        eff_colors: dict[str, str] = dict(DEFAULT_STATUS_COLORS)
        if settings and settings.status_colors:
            eff_colors.update(settings.status_colors)

        bands = ordered_band_names(fieldday.selected_bands)
        export_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        try:
            # Use landscape A4 when many bands
            use_landscape = len(bands) > 6
            pagesize = landscape(A4) if use_landscape else A4
            margin = 15 * mm

            doc = SimpleDocTemplate(
                str(path),
                pagesize=pagesize,
                leftMargin=margin,
                rightMargin=margin,
                topMargin=margin,
                bottomMargin=margin,
                title=f"Field Day Report — {fieldday.name}",
                author="N1MM Field Day Tracker",
                subject="Field Day Station × Band Matrix",
            )

            story = []
            styles = getSampleStyleSheet()
            gen = _ReportGen(fieldday, stations, matrix, bands,
                             eff_colors, styles, export_ts)

            story += gen.title_section()
            story += gen.stats_section()
            story += gen.legend_section()
            story.append(PageBreak())
            story += gen.matrix_section()

            doc.build(story)
            n_pages = 1 + (len(stations) * (len(bands) + 1) // 60)  # estimate
            log.info("PDF export: %d stations, %d bands → %s", len(stations), len(bands), path)
            return ExportResult(path=path, success=True, pages=n_pages)

        except Exception as exc:  # noqa: BLE001
            log.error("PDF export failed: %s", exc)
            return ExportResult(path=path, success=False, error=str(exc))

    @staticmethod
    def default_filename(fieldday: FieldDay) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = fieldday.name.replace(" ", "_")
        return f"{safe_name}_report_{ts}.pdf"


# ── Internal report generator ─────────────────────────────────────────────────

class _ReportGen:
    """Builds the platypus story elements."""

    def __init__(
        self,
        fieldday: FieldDay,
        stations: list[Station],
        matrix: dict[tuple[str, str], StationBandStatus],
        bands: list[str],
        colors_map: dict[str, str],
        styles,
        export_ts: str,
    ) -> None:
        self.fd        = fieldday
        self.stations  = stations
        self.matrix    = matrix
        self.bands     = bands
        self.colors    = colors_map
        self.styles    = styles
        self.export_ts = export_ts

        # Pre-compute stats
        self._compute_stats()

    def _compute_stats(self) -> None:
        m  = self.matrix
        bs = set(self.bands)

        worked = unworked = excluded = overrides = 0
        fully = partially = none_worked = 0

        for s in self.stations:
            nc = s.normalized_callsign
            band_stats = {}
            for b in self.bands:
                cell = m.get((nc, b))
                sv = cell.status if cell else Status.NOT_WORKED
                band_stats[b] = sv

            worked_n = sum(1 for sv in band_stats.values() if sv.is_worked())
            excl_n   = sum(1 for sv in band_stats.values() if sv.is_excluded())
            active   = len(self.bands) - excl_n

            if active == 0:
                none_worked += 1
            elif worked_n == active:
                fully += 1
            elif worked_n > 0:
                partially += 1
            else:
                none_worked += 1

            for b in self.bands:
                cell = m.get((nc, b))
                sv = cell.status if cell else Status.NOT_WORKED
                if sv.is_excluded():     excluded += 1
                elif sv.is_worked():     worked += 1
                else:                    unworked += 1
                if cell and cell.has_override:
                    overrides += 1

        self.stat_worked    = worked
        self.stat_unworked  = unworked
        self.stat_excluded  = excluded
        self.stat_overrides = overrides
        self.stat_fully     = fully
        self.stat_partially = partially
        self.stat_none      = none_worked
        self.stat_total     = len(self.stations)
        self.stat_total_comb = len(self.stations) * len(self.bands)

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------

    def _h(self, text: str, level: int = 1) -> Paragraph:
        sizes = {1: 18, 2: 14, 3: 12}
        style = ParagraphStyle(
            f"h{level}",
            parent=self.styles["Normal"],
            fontSize=sizes.get(level, 11),
            leading=sizes.get(level, 11) + 4,
            fontName="Helvetica-Bold",
            textColor=NAVY,
            spaceAfter=4,
        )
        return Paragraph(text, style)

    def _p(self, text: str, size: int = 10, color=BLACK) -> Paragraph:
        style = ParagraphStyle(
            "body",
            parent=self.styles["Normal"],
            fontSize=size,
            leading=size + 3,
            textColor=color,
        )
        return Paragraph(text, style)

    def _sp(self, h: float = 6) -> Spacer:
        return Spacer(1, h * mm)

    def _hr(self, color=NAVY, thickness=1) -> HRFlowable:
        return HRFlowable(width="100%", thickness=thickness,
                          color=color, spaceAfter=4)

    # ------------------------------------------------------------------
    # Title section
    # ------------------------------------------------------------------

    def title_section(self) -> list:
        story = []

        # Title block
        title_style = ParagraphStyle(
            "title",
            parent=self.styles["Normal"],
            fontSize=24,
            leading=28,
            fontName="Helvetica-Bold",
            textColor=NAVY,
            spaceAfter=4,
        )
        story.append(Paragraph("N1MM Field Day Tracker", title_style))
        story.append(Paragraph("Station × Band Report", ParagraphStyle(
            "sub", parent=self.styles["Normal"],
            fontSize=14, textColor=colors.HexColor("#546e7a"),
            fontName="Helvetica",
        )))
        story.append(self._hr(thickness=2))
        story.append(self._sp(4))

        # Details table
        def _fmt_dt(iso: str) -> str:
            try:
                return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M UTC")
            except (ValueError, TypeError):
                return iso or "—"

        detail_rows = [
            ["Field Day",  self.fd.name or "—"],
            ["Location",   self.fd.location or "—"],
            ["Callsign",   self.fd.event_callsign or "—"],
            ["Organizer",  self.fd.organizer or "—"],
            ["Start",      _fmt_dt(self.fd.start_utc)],
            ["End",        _fmt_dt(self.fd.end_utc)],
            ["Bands",      ", ".join(b.upper() for b in self.bands)],
            ["Exported",   self.export_ts],
        ]
        if self.fd.remarks:
            detail_rows.append(["Remarks", self.fd.remarks])

        tbl = Table(detail_rows, colWidths=[35 * mm, None])
        tbl.setStyle(TableStyle([
            ("FONTNAME",     (0, 0), (-1, -1), "Helvetica"),
            ("FONTNAME",     (0, 0), (0, -1),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 10),
            ("TEXTCOLOR",    (0, 0), (0, -1),  NAVY),
            ("TEXTCOLOR",    (1, 0), (1, -1),  BLACK),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT]),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ]))
        story.append(tbl)
        story.append(self._sp(6))
        return story

    # ------------------------------------------------------------------
    # Statistics section
    # ------------------------------------------------------------------

    def stats_section(self) -> list:
        story = []
        story.append(self._h("Summary Statistics", level=2))
        story.append(self._hr(color=colors.HexColor("#90a4ae"), thickness=0.5))
        story.append(self._sp(2))

        pct = int(100 * self.stat_worked / max(self.stat_total_comb, 1))

        # Big numbers table
        stat_data = [
            ["Total Stations", "Selected Bands", "Combinations",
             "Worked", "Unworked", "Excluded"],
            [
                str(self.stat_total),
                str(len(self.bands)),
                str(self.stat_total_comb),
                str(self.stat_worked),
                str(self.stat_unworked),
                str(self.stat_excluded),
            ],
        ]
        col_w = [30 * mm] * 6
        tbl = Table(stat_data, colWidths=col_w)
        tbl.setStyle(TableStyle([
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTNAME",     (0, 1), (-1, 1),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0),  8),
            ("FONTSIZE",     (0, 1), (-1, 1),  20),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.HexColor("#546e7a")),
            ("TEXTCOLOR",    (3, 1), (3, 1),   colors.HexColor("#2e7d32")),
            ("TEXTCOLOR",    (4, 1), (4, 1),   colors.HexColor("#c62828")),
            ("TEXTCOLOR",    (5, 1), (5, 1),   colors.HexColor("#9e9e9e")),
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
            ("BACKGROUND",   (0, 0), (-1, 0),  LIGHT),
        ]))
        story.append(tbl)
        story.append(self._sp(4))

        # Station-level stats
        stat2_data = [
            ["Fully Worked", "Partially Worked", "Not Worked",
             "Manual Overrides", "Worked %"],
            [
                str(self.stat_fully),
                str(self.stat_partially),
                str(self.stat_none),
                str(self.stat_overrides),
                f"{pct}%",
            ],
        ]
        col_w2 = [35 * mm, 40 * mm, 30 * mm, 40 * mm, 25 * mm]
        tbl2 = Table(stat2_data, colWidths=col_w2)
        tbl2.setStyle(TableStyle([
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTNAME",     (0, 1), (-1, 1),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0),  8),
            ("FONTSIZE",     (0, 1), (-1, 1),  16),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.HexColor("#546e7a")),
            ("TEXTCOLOR",    (0, 1), (0, 1),   colors.HexColor("#2e7d32")),
            ("TEXTCOLOR",    (2, 1), (2, 1),   colors.HexColor("#c62828")),
            ("TEXTCOLOR",    (4, 1), (4, 1),   NAVY),
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
            ("BACKGROUND",   (0, 0), (-1, 0),  LIGHT),
        ]))
        story.append(tbl2)
        story.append(self._sp(6))
        return story

    # ------------------------------------------------------------------
    # Legend section
    # ------------------------------------------------------------------

    def legend_section(self) -> list:
        story = []
        story.append(self._h("Legend", level=2))
        story.append(self._hr(color=colors.HexColor("#90a4ae"), thickness=0.5))
        story.append(self._sp(2))

        legend_items = [
            ("not_worked",        "Not Worked",          "White / empty — no QSO logged"),
            ("worked_by_n1mm",    "Worked (N1MM)",       "Green — QSO received from N1MM Logger+"),
            ("manual_worked",     "Worked (Manual)",     "Dark green — manually marked as worked"),
            ("manual_not_worked", "Not Worked (Manual)", "Amber — manually marked as not worked"),
            ("excluded",          "Excluded",            "Grey — excluded from statistics"),
        ]

        legend_data = [["Colour", "Symbol", "Status", "Description"]]
        for key, label, desc in legend_items:
            hex_bg = self.colors.get(key, DEFAULT_STATUS_COLORS.get(key, "#FFFFFF"))
            sym    = STATUS_SYMBOLS.get(key, "")
            legend_data.append(["", sym, label, desc])

        tbl = Table(legend_data, colWidths=[14 * mm, 14 * mm, 45 * mm, None])

        style_cmds = [
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
            ("ALIGN",        (1, 0), (1, -1),  "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("BACKGROUND",   (0, 0), (-1, 0),  LIGHT),
        ]

        # Apply background colours to swatch column
        for row_i, (key, _, _) in enumerate(legend_items, start=1):
            hex_bg = self.colors.get(key, DEFAULT_STATUS_COLORS.get(key, "#FFFFFF"))
            rl_color = _hex_to_color(hex_bg)
            style_cmds.append(("BACKGROUND", (0, row_i), (0, row_i), rl_color))

        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)
        story.append(self._sp(4))
        return story

    # ------------------------------------------------------------------
    # Matrix section
    # ------------------------------------------------------------------

    def matrix_section(self) -> list:
        story = []
        story.append(self._h("Station × Band Matrix", level=2))
        story.append(self._hr(color=colors.HexColor("#90a4ae"), thickness=0.5))
        story.append(self._sp(2))

        if not self.stations:
            story.append(self._p("No stations imported.", size=10,
                                 color=colors.HexColor("#888")))
            return story

        # Header row: Station + Name/Club + one column per band
        band_labels = [b.upper() for b in self.bands]
        header = ["Station", "Name / Club"] + band_labels

        # Data rows
        table_data = [header]
        row_colors: list[tuple] = []  # (row_idx, col_idx_start, col_idx_end, color)

        for row_i, station in enumerate(
            sorted(self.stations, key=lambda s: s.normalized_callsign), start=1
        ):
            nc = station.normalized_callsign
            sub = " / ".join(x for x in [station.name, station.club] if x)

            row: list = [nc, sub]
            for band in self.bands:
                key = (nc, band)
                cell = self.matrix.get(key)
                sv   = cell.status.value if cell else Status.NOT_WORKED.value
                sym  = STATUS_SYMBOLS.get(sv, "")
                # Add asterisk for override
                if cell and cell.has_override:
                    sym = (sym or "·") + "*"
                row.append(sym)

                hex_bg = self.colors.get(sv, DEFAULT_STATUS_COLORS.get(sv, "#FFFFFF"))
                rl_col_i = 2 + self.bands.index(band)
                row_colors.append((row_i, rl_col_i, _hex_to_color(hex_bg),
                                   _text_color_for_bg(hex_bg)))

            table_data.append(row)

        # Column widths: station 35mm, name 30mm, bands CELL_W_PT each
        station_col_w = 35 * mm
        name_col_w    = 30 * mm
        band_col_w    = CELL_W_PT
        col_widths     = [station_col_w, name_col_w] + [band_col_w] * len(self.bands)

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            # Header
            ("BACKGROUND",   (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0),  8),
            ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
            # Data rows
            ("FONTSIZE",     (0, 1), (-1, -1), 8),
            ("FONTNAME",     (0, 1), (0, -1),  "Helvetica-Bold"),
            ("FONTNAME",     (1, 1), (-1, -1), "Helvetica"),
            ("TEXTCOLOR",    (0, 1), (1, -1),  BLACK),
            ("ALIGN",        (2, 0), (-1, -1), "CENTER"),
            ("ALIGN",        (0, 1), (1, -1),  "LEFT"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            # Padding
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING",  (0, 0), (1, -1),  4),
            ("LEFTPADDING",  (2, 0), (-1, -1), 1),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            # Grid
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            # Alternating row background (data rows only)
        ]

        # Alternating row backgrounds
        for row_i in range(1, len(table_data)):
            if row_i % 2 == 0:
                style_cmds.append(
                    ("BACKGROUND", (0, row_i), (1, row_i),
                     colors.HexColor("#f4f6f8"))
                )

        # Status cell backgrounds
        for row_i, col_i, bg_color, fg_color in row_colors:
            style_cmds.append(("BACKGROUND", (col_i, row_i), (col_i, row_i), bg_color))
            style_cmds.append(("TEXTCOLOR",  (col_i, row_i), (col_i, row_i), fg_color))

        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)

        # Footer note
        story.append(self._sp(4))
        story.append(self._p(
            f"* = manual override active  |  "
            f"Generated by N1MM Field Day Tracker  |  {self.export_ts}",
            size=7,
            color=colors.HexColor("#888888"),
        ))
        return story
