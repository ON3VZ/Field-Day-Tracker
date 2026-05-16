# N1MM Field Day Tracker

A lightweight, offline Windows desktop application that tracks which participating
stations have been worked on which bands during a Field Day event. It integrates
with **N1MM Logger+** via real-time UDP broadcasts and stores all data locally in
plain JSON files — no database, no server, no cloud required.

---

## Quick Start

### 1. Install Python

Download Python 3.11 or later from https://www.python.org/downloads/  
During install: ✅ check **"Add Python to PATH"**

### 2. Create a project folder and virtual environment

```cmd
mkdir C:\N1MM_FieldDay
cd C:\N1MM_FieldDay
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```cmd
pip install -r requirements.txt
```

### 4. Run the application (development mode)

```cmd
python app\main.py
```

---

## N1MM Logger+ Configuration

N1MM Logger+ must be configured to broadcast Contact data to this application.

### Steps in N1MM Logger+

1. Open N1MM Logger+
2. Go to **Config → Configure Ports, Mode Control, Audio, Other**
3. Click the **Broadcast Data** tab
4. Find the **Contact** row and check the **Enable** checkbox
5. In the **Destination** field for Contact, enter: `127.0.0.1:12060`
6. Click **OK**

> **Important:** Use contest **`FDREG1`** in N1MM Logger+ for Field Day events.

### What gets broadcast

N1MM sends a `<contactinfo>` XML message over UDP for every logged contact.
This application listens on `127.0.0.1:12060` (configurable) and processes
those messages in real time.

---

## Folder Structure

```
N1MM Field Day Tracker/
├── app/
│   ├── main.py                    # Application entry point
│   ├── ui/
│   │   ├── main_window.py         # Main application window
│   │   ├── matrix_view.py         # Station × Band matrix
│   │   ├── fieldday_dialog.py     # Create/edit field day dialog
│   │   └── settings_dialog.py     # Settings dialog
│   ├── core/
│   │   ├── models.py              # Data models (FieldDay, Station, QSO, ...)
│   │   ├── band_plan.py           # Band definitions + frequency→band mapping
│   │   ├── callsign.py            # Callsign normalisation
│   │   ├── matching.py            # QSO→station matching logic
│   │   ├── sync_engine.py         # Sync/recalculate engine
│   │   └── status.py              # Status definitions and colours
│   ├── integrations/
│   │   ├── n1mm_udp_listener.py   # UDP listener thread
│   │   └── n1mm_parser.py         # N1MM XML message parser
│   ├── storage/
│   │   ├── json_store.py          # Atomic JSON read/write
│   │   └── fieldday_repository.py # Field day CRUD operations
│   ├── importers/
│   │   └── csv_importer.py        # Station CSV import
│   ├── exporters/
│   │   ├── csv_exporter.py        # CSV export
│   │   └── pdf_exporter.py        # PDF report export
│   └── i18n/
│       └── translations.py        # All UI strings in EN/NL/FR/ES
├── tests/
│   ├── test_callsign.py
│   ├── test_band_plan.py
│   ├── test_matching.py
│   └── test_sync_engine.py
├── fielddays/                     # Created automatically; one subfolder per event
│   └── <fieldday_name>/
│       ├── fieldday.json
│       ├── stations.json
│       ├── received_qsos.json
│       ├── overrides.json
│       ├── sync_log.json
│       └── exports/
├── app_settings.json              # Global settings + last active field day
├── requirements.txt
└── README.md
```

---

## CSV Station Import Format

The CSV file determines which stations participate in the Field Day.
N1MM contacts from stations **not** in this list are silently ignored.

**Required column:** `callsign`  
**Optional columns:** `name`, `club`, `remarks`

**Example:**
```csv
callsign,name,club,remarks
ON3VZ,Cornelis,WLD,
ON4ABC,,,
ON5XY,Jan,UBA,Club secretary
```

Rules:
- One callsign per line
- Callsigns are normalised (case-insensitive, `/P` `/M` `/QRP` stripped if strict=false)
- Duplicate callsigns in the CSV are deduplicated (first occurrence wins)
- Re-importing a CSV preserves existing manual overrides

---

## Field Day Management

- **New field day:** File → New Field Day  
  Set name, location, event callsign, organizer, start/end time (UTC), bands, and N1MM settings.
- **Open field day:** File → Open Field Day  
- **Switch active field day:** File → Switch Field Day  
  Only one field day can be active at a time.
- **Edit field day:** File → Edit Field Day Settings

---

## Matrix View

The main screen shows a **Station × Band** matrix:

| Station | 160m | 80m | 40m | 20m | ... |
|---------|------|-----|-----|-----|-----|
| ON3VZ   | 🟩   | ⬜  | 🟩  | ⬜  | ... |
| ON4ABC  | ⬜   | 🟩  | ⬜  | ⬜  | ... |

**Cell colours (default):**
- ⬜ White — not worked
- 🟩 Green — worked (via N1MM)
- 🟢 Dark green — manually marked as worked
- 🟡 Yellow — manually marked as not worked
- ⬜ Grey — excluded

**Filters:** All / Worked / Unworked / Partially Worked + band filter + search box

---

## Manual Overrides

Right-click any station+band cell to set a manual override:
- **Mark as Worked** — overrides N1MM data
- **Mark as Not Worked** — overrides N1MM data
- **Exclude** — removes from statistics
- **Clear Override** — returns to automatic N1MM status

Manual overrides are stored per **callsign + band** and always take priority.

---

## Settings

Settings are stored in `app_settings.json` and survive restarts.

| Setting | Description | Default |
|---------|-------------|---------|
| `ui_language` | Interface language (en/nl/fr/es) | `en` |
| `n1mm_udp_host` | UDP listen address | `127.0.0.1` |
| `n1mm_udp_port` | UDP listen port | `12060` |
| `freshness_threshold_seconds` | Seconds before connection shown as stale | `30` |
| `strict_callsign_matching` | Exact match vs. normalised match | `false` |
| `default_selected_bands` | Bands pre-selected for new field days | `160m,80m,40m` |
| `status_colors` | Colour overrides for each status | *(see settings dialog)* |
| `export_folder` | Default export folder | `exports/` |

---

## Export

- **CSV Export:** File → Export → CSV  
  Columns: callsign, normalized_callsign, band, status, source, mode, frequency, worked_timestamp_utc, manual_override, remarks

- **PDF Report:** File → Export → PDF Report  
  Includes: title, field day details, statistics summary, legend, full station×band matrix.

---

## Build as Windows .exe

```cmd
venv\Scripts\activate
pip install pyinstaller
pyinstaller --onefile --windowed --name "N1MM Field Day Tracker" app\main.py
```

The executable will appear in the `dist\` folder.
App data (field days, settings) are stored relative to the executable's location.

---

## Troubleshooting UDP Connection

**Problem:** Connection shown as "No data" or "Stale"  
**Solutions:**
1. Check that N1MM Logger+ is running and the contest is active
2. Verify Broadcast Data → Contact is enabled with destination `127.0.0.1:12060`
3. Check Windows Firewall is not blocking port 12060
4. Confirm the host/port in the app Settings matches N1MM configuration
5. Log a test QSO in N1MM and watch the connection status indicator

**Problem:** QSOs received but station not appearing in matrix  
**Solutions:**
1. The station's callsign may not be in the imported station CSV
2. The QSO timestamp may be outside the field day start/end window
3. Check if strict callsign matching is filtering the call (try turning it off)

---

## Architecture Notes

- **No database** — all data in JSON files, one folder per field day
- **Offline first** — works without internet
- **UTC everywhere** — all timestamps stored and compared in UTC
- **Separation of concerns** — business logic is separate from UI
- **Testable** — sync engine and matching logic have no UI dependencies
