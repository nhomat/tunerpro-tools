@echo off
REM =====================================================================
REM  TunerPro Tools Suite - build_all.bat
REM
REM  1. Installs/verifies Python dependencies
REM  2. Runs the automated test suite
REM  3. Compiles every tool into a standalone .exe with PyInstaller
REM  4. Places every .exe directly under dist\
REM  5. Zips the result into TunerProToolsSuite-Windows.zip
REM
REM  Run this on WINDOWS with Python 3.10+ installed and on PATH.
REM  PyInstaller cannot cross-compile: running this script on Linux/macOS
REM  produces Linux/macOS binaries, not Windows .exe files.
REM =====================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [1/5] Installation/verification des dependances...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERREUR: echec de l'installation des dependances.
    exit /b 1
)

echo [2/5] Execution des tests automatises...
python -m pytest tests -q
if errorlevel 1 (
    echo ERREUR: des tests ont echoue. Compilation annulee.
    exit /b 1
)

echo [3/5] Generation des fichiers d'exemple...
python examples\generate_examples.py

echo [4/5] Compilation de tous les outils avec PyInstaller...
if exist dist rmdir /s /q dist
if exist build\pyinstaller_work rmdir /s /q build\pyinstaller_work
python -m PyInstaller --noconfirm --distpath dist --workpath build\pyinstaller_work build\tunerpro_tools.spec
if errorlevel 1 (
    echo ERREUR: la compilation PyInstaller a echoue.
    exit /b 1
)

echo [4b/5] Copie des executables vers TunerPro_CustomTools\...
if not exist TunerPro_CustomTools mkdir TunerPro_CustomTools
copy /y dist\*.exe TunerPro_CustomTools\ >nul

echo [5/5] Creation de l'archive TunerProToolsSuite-Windows.zip...
if exist TunerProToolsSuite-Windows.zip del TunerProToolsSuite-Windows.zip
powershell -NoProfile -Command "Compress-Archive -Path 'dist\*.exe','docs','TunerPro_CustomTools_Setup.txt','install_tunerpro_tools.bat','examples\example_original.bin','examples\example_modified.bin' -DestinationPath 'TunerProToolsSuite-Windows.zip' -Force"

echo.
echo Build termine. Executables dans dist\, archive TunerProToolsSuite-Windows.zip creee.
endlocal
