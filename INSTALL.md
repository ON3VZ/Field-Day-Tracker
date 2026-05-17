# N1MM Field Day Tracker — Installation Guide

This guide is for **end users** who received the pre-built application.
No Python installation or technical knowledge required.

---

## Quick Install (recommended)

1. **Download** `N1MM Field Day Tracker.zip` from the Releases page
2. **Unzip** it to a folder of your choice, e.g.:
   ```
   C:\Users\YourName\N1MM Field Day Tracker\
   ```
3. **Double-click** `N1MM Field Day Tracker.exe` to start

> ⚠️ **Important:** Keep all files in the same folder.  
> Do **not** move just the `.exe` — it needs the `_internal` folder next to it.

---

## First time setup

### Step 1 — Create a Field Day

1. Click **File → New Field Day**
2. Fill in:
   - **Name** — used as the folder name (letters, digits, `-` and `_` only)
   - **Location** — where you are operating from
   - **Event Callsign** — the callsign used on air
   - **Start / End (UTC)** — the field day period in UTC
   - **Selected Bands** — check all bands you will operate on
3. Click **Save**

### Step 2 — Import your station list

1. Prepare a CSV file with at least a `callsign` column:
   ```
   callsign,name,club,remarks
   ON3VZ,Cornelis,WLD,
   ON4ABC,,,
   ```
2. Click **File → Import Station CSV** (or `Ctrl+I`)
3. Select your CSV file

### Step 3 — Configure N1MM Logger+

In N1MM Logger+:
1. **Config → Configure Ports, Mode Control, Audio, Other**
2. Click the **Broadcast Data** tab
3. Find **Contact** → check **Enable**
4. Set Destination: `127.0.0.1:12060`
5. Click **OK**
6. Use contest: **FDREG1**

Once configured, the status bar at the bottom shows **"N1MM: Connected"**
within seconds of logging a contact.

---

## During the Field Day

- The **matrix view** updates automatically as contacts are logged in N1MM
- **Green cells** = station worked on that band
- **White cells** = not yet worked — your targets!
- Use the **⚡ Open** filter to show only stations with open bands
- **Right-click** any cell to manually mark worked/not worked

### Manual sync

If you restart the app or miss some contacts:
- **Tools → Manual Sync / Recalculate** (or `Ctrl+R`)

---

## Live web publishing (optional)

Share the matrix live with people at home via GitHub Pages.
See **Tools → Settings → 📡 Publish tab** for setup instructions.

---

## Export results

- **File → Export → CSV** — full matrix as spreadsheet
- **File → Export → PDF Report** — professional printable report

---

## Troubleshooting

### Status bar shows "N1MM: Waiting…" or "No recent data"

1. Check N1MM Logger+ is running with contest **FDREG1**
2. Verify Broadcast Data → Contact is enabled at destination `127.0.0.1:12060`
3. Check Windows Firewall is not blocking UDP port 12060:
   - Windows Security → Firewall → Advanced Settings
   - Inbound Rules → New Rule → Port → UDP → 12060 → Allow

### The app won't start

- Make sure all files from the zip are in the same folder
- Right-click the `.exe` → Properties → Unblock (if Windows marked it unsafe)
- Try running as Administrator (right-click → Run as administrator)

### Field day data location

App data is stored **next to the executable**:
```
N1MM Field Day Tracker\
├── N1MM Field Day Tracker.exe
├── _internal\                  ← do not delete
├── app_settings.json           ← your settings
└── fielddays\
    └── MyFieldDay2025\         ← your field day data
```

**Back up the `fielddays\` folder** to keep your data safe.

---

## Uninstall

Simply delete the entire `N1MM Field Day Tracker\` folder.
No registry entries are created.

---

## Settings location (onefile build only)

If you use the single-file `.exe` variant, data is stored at:
```
%LOCALAPPDATA%\N1MM_FDT\
```
(e.g. `C:\Users\YourName\AppData\Local\N1MM_FDT\`)
