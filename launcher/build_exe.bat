@echo off
REM Builds a standalone Palversation folder with PyInstaller. Run this
REM from an activated venv (venv\Scripts\activate) that already has
REM requirements.txt installed.
REM
REM Antivirus false-positive mitigations baked into this script (all
REM automatic -- none of these require repeating a manual step per
REM release):
REM
REM   1. "pip install --upgrade pyinstaller" always pulls the latest
REM      bootloader, which PyInstaller periodically recompiles to dodge
REM      stale AV signatures.
REM   2. --onedir instead of --onefile: skips the self-extraction-to-
REM      temp-folder pattern that AV heuristics associate with malware
REM      packers.
REM   3. --noupx: skips UPX compression even if UPX happens to be
REM      installed/on PATH on the build machine. UPX-compressed
REM      PyInstaller binaries get flagged far more often.
REM
REM For an even lower false-positive rate, also run
REM setup_local_bootloader.bat once (not per release) to compile a
REM locally-built bootloader instead of the shared PyPI one.
REM
REM NOTE on --onedir: users get a Palversation\ folder (exe + an
REM _internal\ subfolder) instead of a single exe. Distribute the whole
REM folder zipped, NOT just the exe -- it will not run without
REM _internal\ next to it.
REM
REM Icons: put an icon.ico file in assets\ before running this -- used
REM both for the .exe's own file icon (via --icon below) and for the
REM window/taskbar icon while it's running. A PNG at assets\icon.png
REM also works for the in-app window icon (just not for the .exe file
REM icon itself -- Windows requires .ico for that one). A logo.png in
REM assets\ shows up next to the title in the header.
REM
REM Everything in assets\ (icons, logo) AND a real pal_data.json in this
REM same folder both get bundled INSIDE the build (via --add-data). A
REM real assets\ folder or pal_data.json placed next to the BUILT exe
REM afterward still takes priority over the bundled copy, so
REM branding/species data stay easy to update without rebuilding.
pip install --upgrade pyinstaller
set ADD_DATA=
if exist pal_data.json (
    echo Found pal_data.json, it will be bundled inside the build.
    set ADD_DATA=--add-data "pal_data.json;."
) else (
    echo No pal_data.json found in this folder -- building without bundled species data.
)
if exist assets (
    set ADD_DATA=%ADD_DATA% --add-data "assets;assets"
)
REM Accept any .ico in assets\, not just one named exactly "icon.ico"
REM (e.g. a hash-named file exported from an icon generator site).
set ICON_FILE=
if exist assets\icon.ico (
    set ICON_FILE=assets\icon.ico
) else (
    for %%F in (assets\*.ico) do if not defined ICON_FILE set ICON_FILE=%%F
)
if defined ICON_FILE (
    echo Using icon: %ICON_FILE%
    pyinstaller --name Palversation --onedir --noupx --windowed --clean --icon="%ICON_FILE%" %ADD_DATA% gui\app.py
) else (
    echo No .ico file found in assets\, building without a custom exe icon.
    pyinstaller --name Palversation --onedir --noupx --windowed --clean %ADD_DATA% gui\app.py
)
echo.
echo ============================================================
echo Done. The Palversation folder is inside "dist" -- zip the WHOLE
echo "dist\Palversation" folder to share it, not just the .exe inside.
echo Palversation.exe will not run on its own without the _internal
echo folder sitting right next to it.
echo.
echo config.json, pal_history.json, pal_prompts.json, etc are all
echo created automatically next to the exe the first time it runs
echo -- you don't need to copy anything for those either.
echo.
echo Remember: Windows caches .exe icons aggressively. If the exe's
echo file icon doesn't look right in Explorer right after building,
echo that's very likely just the icon cache showing a stale one --
echo try renaming the exe or restarting Explorer before assuming
echo something's wrong with the build itself.
echo ============================================================
pause