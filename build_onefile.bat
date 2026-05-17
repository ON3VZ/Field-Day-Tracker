@echo off
REM ============================================================
REM  build_onefile.bat
REM  Builds a SINGLE .exe file (--onefile mode).
REM
REM  Pro: One file to copy/share.
REM  Con: First launch takes 5-15 seconds to unpack.
REM       App data stored in %LOCALAPPDATA%\N1MM_FDT\ instead of
REM       next to the exe.
REM
REM  Use build.bat for the recommended --onedir build instead.
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo  Building single-file executable...
echo.

pip install -r requirements.txt --quiet
pip install pillow --quiet 2>nul
python build_assets.py

if exist "dist\N1MM Field Day Tracker.exe" del "dist\N1MM Field Day Tracker.exe"
if exist "build" rmdir /s /q "build"

pyinstaller N1MM_FDT.spec ^
    --onefile ^
    --windowed ^
    --name "N1MM Field Day Tracker" ^
    --noconfirm ^
    --icon assets\icon.ico ^
    app\main.py

if exist "dist\N1MM Field Day Tracker.exe" (
    echo.
    echo  ✅  Single-file exe ready:
    echo      dist\N1MM Field Day Tracker.exe
    echo.
    echo  NOTE: App data will be stored in:
    echo      %%LOCALAPPDATA%%\N1MM_FDT\
) else (
    echo  [ERROR] Build failed.
)

pause
endlocal
