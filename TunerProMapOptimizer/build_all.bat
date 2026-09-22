@echo off
REM =====================================================================
REM  Map Optimizer Assistant - build_all.bat
REM  1. Installs dependencies, 2. runs tests, 3. compiles MapOptimizer.exe
REM  Run on WINDOWS with Python 3.10+ on PATH.
REM  PyInstaller does not cross-compile - run this ON Windows for a .exe.
REM =====================================================================
setlocal
cd /d "%~dp0"

echo [1/3] Installation des dependances...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [2/3] Execution des tests automatises...
python -m pytest tests -q
if errorlevel 1 (
    echo ERREUR: des tests ont echoue. Compilation annulee.
    exit /b 1
)

echo [3/3] Compilation avec PyInstaller...
if exist dist rmdir /s /q dist
if exist build\pyinstaller_work rmdir /s /q build\pyinstaller_work
python -m PyInstaller --noconfirm --distpath dist --workpath build\pyinstaller_work build\map_optimizer.spec
if errorlevel 1 exit /b 1

echo.
echo Build termine : dist\MapOptimizer.exe
endlocal
