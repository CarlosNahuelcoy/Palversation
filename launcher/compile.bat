@echo off
REM Activates the local venv and runs build_exe.bat, so compiling the
REM .exe is a single command instead of two separate steps every time.
REM Run this from the launcher/ folder (same place build_exe.bat lives).

if not exist "venv\Scripts\activate.bat" (
    echo [compile] Could not find venv\Scripts\activate.bat
    echo [compile] Create the venv first:
    echo [compile]   python -m venv venv
    echo [compile]   venv\Scripts\activate
    echo [compile]   pip install -r requirements.txt
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

call build_exe.bat

echo.
echo [compile] Done. Check the dist\ folder for Palversation.exe
pause
