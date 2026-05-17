"""
build_assets.py
===============
Pre-build script that generates required assets for the PyInstaller build:

  1. assets/icon.ico   – application icon (multi-resolution)
  2. version_info.txt  – Windows version resource (shown in file properties)

Run once before building:
    python build_assets.py

Requirements: Pillow (only needed for icon generation, not runtime)
    pip install pillow
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

APP_NAME    = "N1MM Field Day Tracker"
APP_VERSION = "1.0.0"
ASSETS_DIR  = Path("assets")

# ---------------------------------------------------------------------------
# Icon generation
# ---------------------------------------------------------------------------

def create_icon() -> Path:
    """Generate a simple SVG-based icon and convert to .ico."""
    ASSETS_DIR.mkdir(exist_ok=True)
    ico_path = ASSETS_DIR / "icon.ico"

    try:
        from PIL import Image, ImageDraw, ImageFont
        _create_pillow_icon(ico_path)
    except ImportError:
        print("Pillow not installed — generating minimal .ico fallback.")
        _create_minimal_ico(ico_path)

    print(f"✅  Icon created: {ico_path}")
    return ico_path


def _create_pillow_icon(path: Path) -> None:
    """Create a nice icon using Pillow."""
    from PIL import Image, ImageDraw

    sizes = [256, 128, 64, 48, 32, 16]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d   = ImageDraw.Draw(img)

        # Background circle
        pad = size // 8
        d.ellipse([pad, pad, size - pad, size - pad],
                  fill="#1e3a5f")

        # Inner lighter circle
        pad2 = size // 4
        d.ellipse([pad2, pad2, size - pad2, size - pad2],
                  fill="#2a5298")

        # Radio wave arcs (simplified as rectangles for compatibility)
        cx, cy = size // 2, size // 2
        arc_color = "#aac4e0"
        thickness = max(1, size // 20)

        for r in [size // 3, size * 2 // 5]:
            d.arc([cx - r, cy - r, cx + r, cy + r],
                  start=200, end=340, fill=arc_color, width=thickness)

        # Centre dot (antenna)
        dot = max(2, size // 12)
        d.ellipse([cx - dot, cy - dot, cx + dot, cy + dot],
                  fill="#ffffff")

        images.append(img)

    images[0].save(
        str(path),
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )


def _create_minimal_ico(path: Path) -> None:
    """Create a 16×16 minimal .ico without Pillow (pure bytes)."""
    # Simple 16x16 blue square ICO
    # ICO header + directory + BMP data (minimal valid .ico)
    size = 16

    # ICONDIRENTRY
    bmp_data = _make_bmp_16x16()

    ico_header  = struct.pack("<HHH", 0, 1, 1)  # reserved, type=1, count=1
    ico_entry   = struct.pack("<BBBBHHII",
        size, size, 0, 0,  # width, height, colorCount, reserved
        1, 32,             # planes, bitCount
        len(bmp_data),     # bytesInRes
        6 + 16,            # imageOffset (header + 1 entry)
    )
    path.write_bytes(ico_header + ico_entry + bmp_data)


def _make_bmp_16x16() -> bytes:
    """Create a minimal 16×16 ARGB BMP for use in an .ico."""
    width = height = 16
    # BITMAPINFOHEADER
    hdr = struct.pack("<IiiHHIIiiII",
        40,           # biSize
        width,        # biWidth
        height * 2,   # biHeight (×2 for ICO mask)
        1,            # biPlanes
        32,           # biBitCount
        0,            # biCompression (BI_RGB)
        0,            # biSizeImage
        0, 0,         # biXPelsPerMeter, biYPelsPerMeter
        0, 0,         # biClrUsed, biClrImportant
    )
    # Pixel data: 16×16 navy blue ARGB pixels (stored bottom-up)
    pixel = struct.pack("<BBBB", 0x5f, 0x3a, 0x1e, 0xff)  # BGRA navy
    pixels = pixel * (width * height)
    # AND mask (all zeros = fully opaque), 16 rows × 4 bytes aligned
    mask = b"\x00" * (((width + 31) // 32) * 4 * height)
    return hdr + pixels + mask


# ---------------------------------------------------------------------------
# Version info
# ---------------------------------------------------------------------------

def create_version_info() -> Path:
    """Write a Windows version resource file for PyInstaller."""
    path = Path("version_info.txt")
    major, minor, patch = (int(x) for x in APP_VERSION.split("."))

    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'ON3VZ / WLD'),
         StringStruct(u'FileDescription', u'{APP_NAME}'),
         StringStruct(u'FileVersion', u'{APP_VERSION}'),
         StringStruct(u'InternalName', u'N1MM_FDT'),
         StringStruct(u'LegalCopyright', u'Open Source'),
         StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
         StringStruct(u'ProductName', u'{APP_NAME}'),
         StringStruct(u'ProductVersion', u'{APP_VERSION}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
"""
    path.write_text(content, encoding="utf-8")
    print(f"✅  Version info created: {path}")
    return path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Building assets for {APP_NAME} v{APP_VERSION}")
    create_icon()
    create_version_info()
    print("\nAll assets ready. You can now run:")
    print("  pyinstaller N1MM_FDT.spec")
