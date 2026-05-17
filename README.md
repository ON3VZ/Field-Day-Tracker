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
Key fields used by this application:

| XML field | Description |
|-----------|-------------|
| `<call>` | Callsign of the worked station |
| `<band>` | Band (e.g. `40M`, `2M`) |
| `<rxfreq>` | Frequency in 10-Hz units (e.g. `703000` = 7.030 MHz) |
| `<mode>` | Operating mode (`CW`, `SSB`, `FM`, …) |
| `<timestamp>` | UTC timestamp (`YYYY-MM-DD HH:MM:SS`) |
| `<ID>` | Unique contact ID (used for deduplication) |
| `<contestname>` | Should be `FDREG1` |

If N1MM does not send a `<band>` field, the band is automatically derived from the frequency.

### Connection status

The status bar shows the real-time connection state:

| Status | Meaning |
|--------|---------|
| Waiting… | Listening, no data received yet |
| Connected | Data received within the freshness threshold |
| No recent data | No packet for longer than the threshold (default 30s) |
| Error | UDP socket could not be opened — check host/port in Settings |

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

**Required field:** `callsign` (column name is configurable — see below)  
**Optional fields:** `name`, `club`, `remarks` (column names configurable)

**Default example (standard column names):**
```csv
callsign,name,club,remarks
ON3VZ,Cornelis,WLD,
ON4ABC,,,
ON5XY,Jan,UBA,Club secretary
```

**Supported delimiters:** comma, semicolon, tab, pipe (auto-detected)  
**Encoding:** UTF-8 or UTF-8 with BOM (Excel export works directly)

### CSV Column Mapping

If your CSV uses different column headers, configure the mapping in  
**Tools → Settings → CSV Column Mapping**.

| Internal field | Default CSV column | Example alternative |
|---------------|-------------------|---------------------|
| callsign | callsign | Roepnaam, Call, Indicatif |
| name | name | Naam, Nom, Operator |
| club | club | Club, Organisation |
| remarks | remarks | Opmerkingen, Notes |

Use **"Detect Columns from CSV…"** in the settings to preview the headers in your file before mapping them.

### Re-import Rules

- Existing **manual overrides** are always preserved
- **Manually added** stations are always kept
- Stations **absent from the new CSV** are flagged — you will be asked before they are removed
- Duplicate callsigns in the CSV → first occurrence wins

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

Open via **Tools → Settings** (or toolbar ⚙ button).

### General tab

| Setting | Description | Default |
|---------|-------------|---------|
| **Interface Language** | EN / NL / FR / ES — takes effect immediately | `en` |
| **Strict Callsign Matching** | OFF: ON3VZ/P matches ON3VZ. ON: exact match only | OFF |
| **Default Bands** | Bands pre-ticked when creating a new field day | 160m, 80m, 40m |

### N1MM / UDP tab

| Setting | Description | Default |
|---------|-------------|---------|
| **UDP Host** | IP address to listen on (127.0.0.1 = same PC) | `127.0.0.1` |
| **UDP Port** | Must match N1MM Broadcast Data destination | `12060` |
| **Freshness Threshold** | Seconds before connection shown as stale | `30` |

The tab also shows the N1MM setup guide (steps 1–5) for quick reference.

### Appearance tab

Customise the background colour of each matrix cell status.
Click any colour swatch or **Choose…** to open a colour picker.
Changes preview immediately. **Reset to defaults** restores factory colours.

| Status | Default colour |
|--------|----------------|
| Not Worked | White `#FFFFFF` |
| Worked (N1MM) | Green `#4CAF50` |
| Worked (Manual) | Dark green `#1B5E20` |
| Not Worked (Manual) | Amber `#FFC107` |
| Excluded | Grey `#9E9E9E` |

### CSV Mapping tab

Map your CSV column headers to internal field names.
Use **Detect Columns from CSV…** to preview the headers in a file.

| Internal field | Default CSV column |
|---------------|-------------------|
| callsign (required) | `callsign` |
| name | `name` |
| club | `club` |
| remarks | `remarks` |

### Export tab

Set the default folder where CSV and PDF exports are saved.

---

## Sync / Recalculate

### Automatic sync
Every time N1MM Logger+ sends a contact via UDP, the matrix updates in real time — no action needed.

### Manual sync
**Tools → Manual Sync / Recalculate** re-processes all stored QSOs from scratch. Use this after:
- Changing field day settings (bands, period, strict matching)
- A crash or missed UDP packets
- Importing a new station CSV

### Business rules (always enforced)
| Rule | Description |
|------|-------------|
| **Manual override wins** | Always, unconditionally — even if N1MM logs the same contact again |
| **Period filter** | QSOs outside start/end window are ignored |
| **Unknown stations** | N1MM contacts not in the station list are silently ignored |
| **Callsign + band** | Status is per callsign+band, not per QSO count |
| **UTC** | All timestamps stored and compared in UTC |
| **Band from frequency** | If N1MM doesn't send a band name, it is derived from the frequency |
| **Strict matching** | Configurable — `/P` `/M` `/QRP` suffixes stripped when off |

- **CSV Export:** File → Export → CSV  
  Columns: callsign, normalized_callsign, band, status, source, mode, frequency, worked_timestamp_utc, manual_override, remarks

- **PDF Report:** File → Export → PDF Report  
  Includes: title, field day details, statistics summary, legend, full station×band matrix.

---

## Help System

Context-sensitive help is available **everywhere** in the application:

| How | Action |
|-----|--------|
| **F1 key** | Opens help for the current screen or dialog |
| **? button** | Every dialog has a `?` button in the top-right corner |
| **Help menu** | Access any topic from the menu bar |

**Available help topics:** Main Window, Matrix View, Connection Status, Field Day Settings, Field Day Period, Band Selection, CSV Import, CSV Column Mapping, Add Station Manually, N1MM Setup, N1MM UDP Settings, Callsign Matching, Manual Overrides, Settings, Language Setting, Status Colours, CSV Export, PDF Export, Sync/Recalculate.

All help texts are available in **English, Dutch, French and Spanish**.

---

## Data Storage

All data is stored locally in plain JSON files — no database, no server required.

```
app_settings.json              ← global settings + last active field day
fielddays/
└── <fieldday_name>/
    ├── fieldday.json          ← metadata, bands, period, N1MM settings
    ├── stations.json          ← imported + manually added stations
    ├── received_qsos.json     ← all QSOs received from N1MM via UDP
    ├── overrides.json         ← manual status overrides (callsign + band)
    ├── sync_log.json          ← sync history (last 100 entries)
    └── exports/               ← CSV and PDF exports
```

**Safe atomic writes:** all JSON files are written via a temp-file-then-replace pattern. If the application crashes mid-write, the original file is always intact.

---

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

## Running Tests

```cmd
cd C:\N1MM_FieldDay
venv\Scripts\activate
python -m unittest discover tests -v
```

All business logic is tested independently of the GUI:

| Test file | What it covers |
|-----------|---------------|
| `tests/test_callsign.py` | Normalisation, strict/non-strict matching, validation |
| `tests/test_band_plan.py` | Band lookup, frequency→band, N1MM freq field parsing |
| `tests/test_models.py` | FieldDay period, serialisation round-trips |
| `tests/test_storage.py` | Atomic writes, repository CRUD, sync log |
| `tests/test_csv_importer.py` | Import, re-import, column mapping, edge cases |
| `tests/test_matching.py` | QSO↔station matching, band resolution |
| `tests/test_sync_engine.py` | All 7 business rules, real-time update, statistics |
| `tests/test_n1mm_parser.py` | XML parsing, frequency conversion, edge cases |
| `tests/test_app_controller.py` | Controller: field day CRUD, sync, overrides, CSV, observers |

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

## Architecture Notes

- **No database** — all data in JSON files, one folder per field day
- **Offline first** — works without internet
- **UTC everywhere** — all timestamps stored and compared in UTC
- **Separation of concerns** — business logic is separate from UI
- **Testable** — sync engine and matching logic have no UI dependencies
- **Safe writes** — atomic temp-file-then-replace for all JSON files
- **Configurable CSV** — column mapping makes any CSV format work
- **Help everywhere** — F1 + ? button on every screen, 4 languages
- **AppController** — single coordinator owns all state; UI only calls its methods
- **Observer pattern** — UDP listener notifies UI via callbacks, marshalled via `root.after()`
