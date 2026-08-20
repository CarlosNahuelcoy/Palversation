@echo off
REM ============================================================
REM ONE-TIME SETUP -- run this once per machine, not per release.
REM
REM Compiles a local PyInstaller bootloader instead of using the
REM pre-built one from PyPI. Every PyInstaller user in the world
REM shares the same PyPI-distributed bootloader binary, which is
REM exactly why AV vendors have it flagged in their signature
REM databases -- it's the single most "seen" binary in every
REM false-positive report. Building it locally gives it a unique
REM hash that hasn't been fingerprinted yet, which helps with some
REM AV products (not all).
REM
REM REQUIRES: a C compiler. On Windows this means Visual Studio
REM Build Tools (the "Desktop development with C++" workload).
REM Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
REM If this script fails at the "waf" step, that's almost always
REM a missing/broken C compiler, not a problem with this script.
REM
REM After this finishes, PyInstaller is installed from the local
REM checkout with the freshly-built bootloader. Nothing else in
REM the normal release flow (compile.bat / build_exe.bat) changes --
REM they'll just pick up this bootloader automatically since it's
REM now what "pyinstaller" resolves to in this venv.
REM
REM Re-run this occasionally (not every release) if false positives
REM creep back up over time, since AV vendors do eventually
REM fingerprint locally-built bootloaders too if they see them
REM often enough across many different PyInstaller users.
REM ============================================================

if not exist "venv\Scripts\activate.bat" (
    echo [setup_local_bootloader] No venv found. Create it first:
    echo [setup_local_bootloader]   python -m venv venv
    echo [setup_local_bootloader]   venv\Scripts\activate
    echo [setup_local_bootloader]   pip install -r requirements.txt
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

if exist pyinstaller-src (
    echo [setup_local_bootloader] Removing previous local PyInstaller checkout...
    rmdir /s /q pyinstaller-src
)

echo [setup_local_bootloader] Cloning PyInstaller...
git clone https://github.com/pyinstaller/pyinstaller.git pyinstaller-src
if errorlevel 1 (
    echo [setup_local_bootloader] git clone failed. Is git installed and on PATH?
    pause
    exit /b 1
)

cd pyinstaller-src\bootloader
echo [setup_local_bootloader] Building bootloader from source ^(needs a C compiler^)...
python ./waf all
if errorlevel 1 (
    cd ..\..
    echo [setup_local_bootloader] Bootloader build failed. Make sure Visual Studio
    echo [setup_local_bootloader] Build Tools ^(C++ workload^) is installed, then retry.
    pause
    exit /b 1
)
cd ..

echo [setup_local_bootloader] Installing PyInstaller from local checkout...
pip install .
cd ..

echo.
echo ============================================================
echo Done. This venv now uses a locally-built PyInstaller bootloader.
echo Just run compile.bat as usual for your releases -- no other
echo changes needed. Re-run this setup script again in the future
echo only if false positives start creeping back up.
echo ============================================================
pause
