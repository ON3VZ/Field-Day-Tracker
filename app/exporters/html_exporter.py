"""
app/exporters/html_exporter.py
================================
Generates a standalone, self-contained HTML page showing the
station × band matrix for publication on GitHub Pages.

Design goals
------------
- Single HTML file — no external dependencies, works offline
- Mobile-friendly (responsive grid)
- Identical colours to the desktop matrix
- Auto-refresh every 60 seconds (meta refresh)
- Clear "last updated" indicator
- Readable on phone screen of someone following from home

Public API
----------
HTMLExporter.export(path, fieldday, stations, matrix, settings, live_url)
    → ExportResult
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.band_plan import ordered_band_names
from app.core.models import AppSettings, FieldDay, Station, StationBandStatus
from app.core.status import DEFAULT_STATUS_COLORS, STATUS_SYMBOLS, Status
from app.storage.json_store import ensure_dir

log = logging.getLogger(__name__)


@dataclass
class ExportResult:
    path: Path
    success: bool
    error: str = ""


class HTMLExporter:
    """Generates a self-contained HTML matrix page."""

    @staticmethod
    def export(
        path: Path,
        fieldday: FieldDay,
        stations: list[Station],
        matrix: dict[tuple[str, str], StationBandStatus],
        settings: AppSettings | None = None,
        refresh_seconds: int = 60,
    ) -> ExportResult:
        path = Path(path)
        ensure_dir(path.parent)

        settings = settings or AppSettings()
        eff_colors: dict[str, str] = {**DEFAULT_STATUS_COLORS,
                                       **(settings.status_colors or {})}
        bands = ordered_band_names(fieldday.selected_bands)
        export_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        try:
            html = _build_html(
                fieldday, stations, matrix, bands,
                eff_colors, export_ts, refresh_seconds,
            )
            path.write_text(html, encoding="utf-8")
            log.info("HTML export: %d stations → %s", len(stations), path)
            return ExportResult(path=path, success=True)
        except Exception as exc:  # noqa: BLE001
            log.error("HTML export failed: %s", exc)
            return ExportResult(path=path, success=False, error=str(exc))

    @staticmethod
    def default_filename() -> str:
        return "index.html"


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _build_html(
    fd: FieldDay,
    stations: list[Station],
    matrix: dict[tuple[str, str], StationBandStatus],
    bands: list[str],
    colors: dict[str, str],
    export_ts: str,
    refresh_seconds: int,
) -> str:
    """Build the full HTML document as a string."""

    # ── Statistics ────────────────────────────────────────────────────────────
    total = len(stations)
    worked = unworked = excluded = 0
    fully = partially = none_w = 0

    for s in stations:
        nc = s.normalized_callsign
        w = sum(1 for b in bands
                if matrix.get((nc, b)) and matrix[(nc, b)].status.is_worked())
        ex = sum(1 for b in bands
                 if matrix.get((nc, b)) and matrix[(nc, b)].status.is_excluded())
        active = len(bands) - ex
        worked += w
        excluded += ex
        unworked += max(0, active - w)

        if active == 0:   none_w += 1
        elif w == active: fully += 1
        elif w > 0:       partially += 1
        else:             none_w += 1

    total_comb = total * len(bands)
    pct = int(100 * worked / max(total_comb, 1))

    # ── Matrix rows HTML ─────────────────────────────────────────────────────
    def _cell_html(nc: str, band: str) -> str:
        cell = matrix.get((nc, band))
        sv   = cell.status.value if cell else Status.NOT_WORKED.value
        sym  = STATUS_SYMBOLS.get(sv, "")
        bg   = colors.get(sv, "#FFFFFF")

        # Text colour based on background luminance
        try:
            h = bg.lstrip("#")
            r, g, b_ = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            lum = 0.299 * r + 0.587 * g + 0.114 * b_
            fg = "#000" if lum > 140 else "#fff"
        except (ValueError, IndexError):
            fg = "#000"

        override_mark = " ✎" if (cell and cell.has_override) else ""
        title_parts = [f"Status: {sv.replace('_', ' ')}"]
        if cell and cell.worked_timestamp_utc:
            try:
                dt = datetime.fromisoformat(cell.worked_timestamp_utc)
                title_parts.append(f"Worked: {dt.strftime('%H:%M UTC')}")
            except ValueError:
                pass
        if cell and cell.mode:
            title_parts.append(f"Mode: {cell.mode}")

        title = " | ".join(title_parts)
        return (
            f'<td class="cell" style="background:{bg};color:{fg}" title="{title}">'
            f'{sym}{override_mark}</td>'
        )

    rows_html = []
    for idx, s in enumerate(
        sorted(stations, key=lambda x: x.normalized_callsign)
    ):
        nc  = s.normalized_callsign
        sub = " / ".join(x for x in [s.name, s.club] if x)
        rmk = f'<span class="rmk" title="{s.remarks}">💬</span>' if s.remarks else ""
        row_cls = "odd" if idx % 2 == 0 else "even"

        cells = "".join(_cell_html(nc, b) for b in bands)
        rows_html.append(
            f'<tr class="{row_cls}">'
            f'<td class="stn"><strong>{nc}</strong>'
            f'{f"<br><small>{sub}</small>" if sub else ""}'
            f'{rmk}</td>'
            f'{cells}</tr>'
        )

    band_headers = "".join(
        f'<th class="band-hdr">{b.upper()}</th>' for b in bands
    )

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_items = [
        ("not_worked",        "Not Worked"),
        ("worked_by_n1mm",    "Worked (N1MM)"),
        ("manual_worked",     "Worked (Manual)"),
        ("manual_not_worked", "Not Worked (Manual)"),
        ("excluded",          "Excluded"),
    ]
    legend_html = "".join(
        f'<span class="leg-item">'
        f'<span class="leg-swatch" style="background:{colors.get(k,"#fff")}">'
        f'{STATUS_SYMBOLS.get(k,"")}</span>'
        f'<span class="leg-label">{label}</span>'
        f'</span>'
        for k, label in legend_items
    )

    # ── Period ────────────────────────────────────────────────────────────────
    def _fmt(iso: str) -> str:
        try:
            return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError):
            return iso or "—"

    period_str = f"{_fmt(fd.start_utc)}  →  {_fmt(fd.end_utc)}"

    # ── Full HTML ─────────────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{refresh_seconds}">
<title>{fd.name} — Field Day Tracker</title>
<style>
  /* ── Reset & base ─────────────────────────────────────── */
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Segoe UI", system-ui, sans-serif;
          background: #f5f5f5; color: #212121; font-size: 14px; }}

  /* ── Header ──────────────────────────────────────────── */
  .hdr {{ background: #1e3a5f; color: #fff; padding: 14px 20px; }}
  .hdr h1 {{ font-size: 1.4rem; font-weight: 700; }}
  .hdr .sub {{ color: #aac4e0; font-size: 0.85rem; margin-top: 2px; }}

  /* ── Stats bar ───────────────────────────────────────── */
  .stats {{ display: flex; flex-wrap: wrap; gap: 0;
            background: #e8eaf6; border-bottom: 1px solid #c5cae9; }}
  .stat {{ flex: 1 1 80px; text-align: center; padding: 10px 6px; }}
  .stat .num {{ font-size: 1.8rem; font-weight: 700; line-height: 1; }}
  .stat .lbl {{ font-size: 0.7rem; color: #555; margin-top: 2px; }}
  .num-open    {{ color: #c62828; }}
  .num-partial {{ color: #ef6c00; }}
  .num-done    {{ color: #2e7d32; }}
  .num-total   {{ color: #1e3a5f; }}

  /* ── Progress bar ────────────────────────────────────── */
  .prog-wrap {{ padding: 8px 16px 10px; background: #e8eaf6;
                border-bottom: 2px solid #c5cae9; }}
  .prog-bar {{ height: 14px; border-radius: 7px; overflow: hidden;
               background: #ef9a9a; display: flex; }}
  .prog-done    {{ background: #43a047; transition: width .3s; }}
  .prog-partial {{ background: #ef6c00; transition: width .3s; }}
  .prog-label   {{ font-size: 0.75rem; color: #555; margin-top: 4px;
                   text-align: center; }}

  /* ── Content ─────────────────────────────────────────── */
  .content {{ padding: 12px 16px; overflow-x: auto; }}

  /* ── Legend ──────────────────────────────────────────── */
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px;
             margin-bottom: 12px; font-size: 0.8rem; }}
  .leg-item {{ display: flex; align-items: center; gap: 5px; }}
  .leg-swatch {{ display: inline-block; width: 24px; height: 18px;
                 border: 1px solid #bbb; border-radius: 3px;
                 text-align: center; font-size: 0.75rem; line-height: 18px; }}
  .leg-label {{ color: #444; }}

  /* ── Matrix table ────────────────────────────────────── */
  .matrix {{ border-collapse: collapse; min-width: 100%; }}
  .matrix th {{ background: #1e3a5f; color: #fff; font-size: 0.78rem;
                padding: 6px 4px; text-align: center;
                position: sticky; top: 0; z-index: 2; }}
  .matrix th.stn-hdr {{ text-align: left; padding-left: 8px;
                         min-width: 130px; position: sticky;
                         left: 0; z-index: 3; }}
  .matrix .band-hdr {{ min-width: 52px; }}
  .matrix td {{ padding: 4px 2px; border: 1px solid #e0e0e0;
                text-align: center; font-size: 0.85rem; }}
  .matrix td.stn {{ text-align: left; padding: 4px 8px;
                    position: sticky; left: 0; z-index: 1;
                    background: inherit; min-width: 130px; }}
  .matrix tr.odd  td.stn {{ background: #fff; }}
  .matrix tr.even td.stn {{ background: #f4f6f8; }}
  .matrix tr.odd  {{ background: #fff; }}
  .matrix tr.even {{ background: #f4f6f8; }}
  .matrix tr:hover {{ background: #e3f2fd !important; }}
  .matrix tr:hover td.stn {{ background: #e3f2fd !important; }}
  .matrix td.cell {{ font-weight: 700; }}
  .rmk {{ margin-left: 4px; font-size: 0.8rem; cursor: help; }}

  /* ── Footer ──────────────────────────────────────────── */
  .footer {{ text-align: center; padding: 12px;
             font-size: 0.75rem; color: #888;
             border-top: 1px solid #e0e0e0; margin-top: 8px; }}
  .refresh-badge {{
    display: inline-block; background: #1e3a5f; color: #aac4e0;
    font-size: 0.7rem; padding: 2px 8px; border-radius: 10px;
    margin-bottom: 4px;
  }}

  /* ── Responsive ──────────────────────────────────────── */
  @media (max-width: 600px) {{
    .hdr h1 {{ font-size: 1.1rem; }}
    .stat .num {{ font-size: 1.4rem; }}
    .matrix {{ font-size: 0.75rem; }}
  }}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <h1>📻 {fd.name} — Field Day Live</h1>
  <div class="sub">
    {fd.event_callsign or ""}{" · " + fd.location if fd.location else ""}
    {" · " + fd.organizer if fd.organizer else ""}
  </div>
  <div class="sub" style="margin-top:4px;font-size:.8rem;">
    📅 {period_str}
  </div>
</div>

<!-- STATS -->
<div class="stats">
  <div class="stat"><div class="num num-open">{none_w}</div>
    <div class="lbl">Open</div></div>
  <div class="stat"><div class="num num-partial">{partially}</div>
    <div class="lbl">Partial</div></div>
  <div class="stat"><div class="num num-done">{fully}</div>
    <div class="lbl">Complete</div></div>
  <div class="stat"><div class="num num-total">{total}</div>
    <div class="lbl">Stations</div></div>
  <div class="stat"><div class="num num-done">{worked}</div>
    <div class="lbl">Worked</div></div>
  <div class="stat"><div class="num num-open">{unworked}</div>
    <div class="lbl">Unworked</div></div>
  <div class="stat"><div class="num num-total">{pct}%</div>
    <div class="lbl">Complete</div></div>
</div>

<!-- PROGRESS BAR -->
<div class="prog-wrap">
  <div class="prog-bar">
    <div class="prog-done"    style="width:{int(100*fully/max(total,1))}%"></div>
    <div class="prog-partial" style="width:{int(100*partially/max(total,1))}%"></div>
  </div>
  <div class="prog-label">{fully} fully · {partially} partial · {none_w} not started</div>
</div>

<!-- CONTENT -->
<div class="content">

  <!-- LEGEND -->
  <div class="legend">{legend_html}</div>

  <!-- MATRIX -->
  <table class="matrix">
    <thead>
      <tr>
        <th class="stn-hdr">Station</th>
        {band_headers}
      </tr>
    </thead>
    <tbody>
      {"".join(rows_html)}
    </tbody>
  </table>

</div>

<!-- FOOTER -->
<div class="footer">
  <div class="refresh-badge">🔄 Auto-refresh every {refresh_seconds}s</div><br>
  Last updated: <strong>{export_ts}</strong><br>
  Published by <em>N1MM Field Day Tracker</em>
  &nbsp;·&nbsp; ✎ = manual override
</div>

</body>
</html>"""
