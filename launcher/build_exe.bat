@echo off
REM Builds a standalone Palversation.exe with PyInstaller. Run this from
REM an activated venv (venv\Scripts\activate) that already has
REM requirements.txt installed.
REM
REM Icons: put an icon.ico file in assets\ before running this -- used
REM both for the .exe's own file icon (via --icon below) and for the
REM window/taskbar icon while it's running. A PNG at assets\icon.png
REM also works for the in-app window icon (just not for the .exe file
REM icon itself -- Windows requires .ico for that one). A logo.png in
REM assets\ shows up next to the title in the header.
REM
REM Everything in assets\ (icons, logo) AND a real pal_data.json in this
REM same folder both get bundled INSIDE the exe (via --add-data), so the
REM single built .exe is fully self-contained -- nothing else needs to
REM ship alongside it. A real assets\ folder or pal_data.json placed
REM next to the BUILT exe afterward still takes priority over the
REM bundled copy, so branding/species data stay easy to update without
REM rebuilding, if you ever want that -- it's just not required anymore.

pip install pyinstaller

set ADD_DATA=
if exist pal_data.json (
    echo Found pal_data.json, it will be bundled inside the exe.
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
    pyinstaller --name Palversation --onefile --windowed --clean --icon="%ICON_FILE%" %ADD_DATA% gui\app.py
) else (
    echo No .ico file found in assets\, building without a custom exe icon.
    pyinstaller --name Palversation --onefile --windowed --clean %ADD_DATA% gui\app.py
)

echo.
echo ============================================================
echo Done. Palversation.exe is inside the "dist" folder -- that
echo single file is now everything you need to share (icons, logo,
echo and species data are all bundled inside it, if you had them in
echo this folder when you ran this script).
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
