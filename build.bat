@echo off
REM ============================================================
REM  build.bat
REM  One-click build script for N1MM Field Day Tracker
REM
REM  Run from the project root with venv active:
REM    venv\Scripts\activate
REM    build.bat
REM
REM  Output: dist\N1MM Field Day Tracker\N1MM Field Day Tracker.exe
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo  ============================================
echo   N1MM Field Day Tracker - Windows Build
echo  ============================================
echo.

REM ── Check Python ────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
    pause & exit /b 1
)

for /f "tokens=*" %%v in ('python --version') do echo  Python: %%v

REM ── Check venv ──────────────────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo [WARN]  No venv found. Creating one...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
) else (
    echo  Venv: found
)

REM ── Install dependencies ────────────────────────────────────
echo  Installing/checking dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause & exit /b 1
)

REM ── Install Pillow for icon generation (build-time only) ────
pip install pillow --quiet 2>nul

REM ── Generate assets ─────────────────────────────────────────
echo  Generating build assets (icon, version info)...
python build_assets.py
if errorlevel 1 (
    echo [WARN]  Asset generation had issues - continuing with fallback icon.
)

REM ── Clean previous build ────────────────────────────────────
if exist "dist\N1MM Field Day Tracker" (
    echo  Cleaning previous build...
    rmdir /s /q "dist\N1MM Field Day Tracker"
)
if exist "build" (
    rmdir /s /q "build"
)

REM ── Run PyInstaller ─────────────────────────────────────────
echo.
echo  Running PyInstaller...
echo  (This may take 1-3 minutes)
echo.

pyinstaller N1MM_FDT.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. See output above.
    pause & exit /b 1
)

REM ── Verify output ───────────────────────────────────────────
set EXE_PATH=dist\N1MM Field Day Tracker\N1MM Field Day Tracker.exe
if not exist "%EXE_PATH%" (
    echo [ERROR] Expected exe not found: %EXE_PATH%
    pause & exit /b 1
)

REM ── Show result ─────────────────────────────────────────────
echo.
echo  ============================================
echo   BUILD SUCCESSFUL
echo  ============================================
echo.
echo  Executable:
echo    %EXE_PATH%
echo.

for %%F in ("%EXE_PATH%") do (
    set /a SIZE_MB=%%~zF / 1048576
    echo  Size: !SIZE_MB! MB
)

echo.
echo  To distribute:
echo    Copy the entire folder:
echo    dist\N1MM Field Day Tracker\
echo    (Do NOT copy just the .exe - it needs the _internal folder)
echo.
echo  Or run the app now:
echo    "%EXE_PATH%"
echo.

choice /c YN /m "Open the output folder now?"
if errorlevel 2 goto :done
explorer "dist\N1MM Field Day Tracker"

:done
endlocal
