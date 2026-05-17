# -*- mode: python ; coding: utf-8 -*-
#
# N1MM_FDT.spec
# =============
# PyInstaller spec file for N1MM Field Day Tracker.
#
# Build command (from project root, with venv active):
#   pyinstaller N1MM_FDT.spec
#
# Output:
#   dist/N1MM Field Day Tracker/N1MM Field Day Tracker.exe  (--onedir)
#
# The --onedir mode is preferred over --onefile because:
#   - First launch is fast (no unpacking)
#   - App data folder is next to the .exe
#   - Easier to update individual files if needed
#
# App data (fielddays/, app_settings.json) is stored in the SAME folder
# as the executable, not inside the bundle.  See app/main.py for the
# APP_ROOT resolution logic.

import sys
from pathlib import Path

APP_NAME    = "N1MM Field Day Tracker"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "app/main.py"
ICON_FILE   = "assets/icon.ico"  # created by build_assets.py

block_cipher = None

# ---------------------------------------------------------------------------
# Analysis: collect all imports and data files
# ---------------------------------------------------------------------------
a = Analysis(
    [MAIN_SCRIPT],
    pathex=['.'],
    binaries=[],
    datas=[
        # No external data files needed — everything is generated at runtime.
        # If you add translation files or icons later, add them here:
        # ("assets/icon.ico", "assets"),
    ],
    hiddenimports=[
        # Standard library modules that PyInstaller may miss
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.colorchooser",
        "tkinter.scrolledtext",
        "tkinter.simpledialog",
        "xml.etree.ElementTree",
        "xml.etree",
        "csv",
        "json",
        "socket",
        "threading",
        "logging",
        "logging.handlers",
        "pathlib",
        "datetime",
        "uuid",
        "platform",
        "getpass",
        "base64",
        "hashlib",
        "tempfile",
        "subprocess",
        "urllib.request",
        "urllib.error",

        # cryptography (for token encryption)
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.backends",

        # reportlab (for PDF export)
        "reportlab",
        "reportlab.lib",
        "reportlab.lib.pagesizes",
        "reportlab.lib.styles",
        "reportlab.lib.units",
        "reportlab.lib.colors",
        "reportlab.lib.enums",
        "reportlab.platypus",
        "reportlab.platypus.tables",
        "reportlab.pdfgen",
        "reportlab.pdfgen.canvas",
        "reportlab.pdfbase",
        "reportlab.pdfbase.pdfmetrics",
        "reportlab.pdfbase._fontdata",
        "reportlab.pdfbase.ttfonts",
        "reportlab.graphics",

        # Our own modules (insurance — PyInstaller usually finds these)
        "app",
        "app.main",
        "app.app_controller",
        "app.core.models",
        "app.core.band_plan",
        "app.core.callsign",
        "app.core.matching",
        "app.core.sync_engine",
        "app.core.status",
        "app.i18n.translations",
        "app.integrations.n1mm_udp_listener",
        "app.integrations.n1mm_parser",
        "app.storage.json_store",
        "app.storage.fieldday_repository",
        "app.importers.csv_importer",
        "app.exporters.csv_exporter",
        "app.exporters.pdf_exporter",
        "app.exporters.html_exporter",
        "app.exporters.github_pages_publisher",
        "app.security.token_store",
        "app.ui.main_window",
        "app.ui.matrix_view",
        "app.ui.fieldday_dialog",
        "app.ui.settings_dialog",
        "app.ui.help_system",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy packages we don't use
        "numpy",
        "pandas",
        "matplotlib",
        "PIL",
        "scipy",
        "pytest",
        "unittest",   # keep for now; remove if size matters
        "email",
        "html",
        "http",
        "ftplib",
        "xmlrpc",
        "pydoc",
        "doctest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------------
# PYZ: compiled bytecode archive
# ---------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# EXE: the Windows executable
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir mode: binaries go next to the exe
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                # compress with UPX if available
    console=False,           # no console window (windowed app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE if Path(ICON_FILE).exists() else None,
    version="version_info.txt" if Path("version_info.txt").exists() else None,
)

# ---------------------------------------------------------------------------
# COLLECT: gather everything into dist/N1MM Field Day Tracker/
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
