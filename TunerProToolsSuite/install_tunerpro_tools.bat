@echo off
REM =====================================================================
REM  TunerPro Tools Suite - install_tunerpro_tools.bat
REM
REM  Installs the already-built .exe files (from dist\, produced by
REM  build_all.bat) into C:\TunerProToolsSuite\, creates the folder
REM  layout the suite expects (Tools, Config, Backups, Reports,
REM  Projects), and creates Desktop/Start Menu shortcuts.
REM
REM  Run this AFTER build_all.bat has produced dist\*.exe.
REM =====================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "INSTALL_ROOT=C:\TunerProToolsSuite"

if not exist dist\*.exe (
    echo ERREUR: aucun .exe trouve dans dist\. Executez d'abord build_all.bat.
    exit /b 1
)

echo Installation dans %INSTALL_ROOT% ...
mkdir "%INSTALL_ROOT%\Tools\TunerPro_CustomTools" 2>nul
mkdir "%INSTALL_ROOT%\Config" 2>nul
mkdir "%INSTALL_ROOT%\Backups\original" 2>nul
mkdir "%INSTALL_ROOT%\Backups\modified" 2>nul
mkdir "%INSTALL_ROOT%\Backups\reports" 2>nul
mkdir "%INSTALL_ROOT%\Reports" 2>nul
mkdir "%INSTALL_ROOT%\Projects" 2>nul
mkdir "%INSTALL_ROOT%\logs" 2>nul

copy /y dist\*.exe "%INSTALL_ROOT%\Tools\TunerPro_CustomTools\" >nul
copy /y config\default_config.json "%INSTALL_ROOT%\Config\" >nul
copy /y examples\example_original.bin "%INSTALL_ROOT%\Projects\" >nul
copy /y examples\example_modified.bin "%INSTALL_ROOT%\Projects\" >nul

echo Creation des raccourcis...
set "DESKTOP=%USERPROFILE%\Desktop"
powershell -NoProfile -Command ^
  "$s = (New-Object -COM WScript.Shell).CreateShortcut('%DESKTOP%\TunerPro Tools Suite.lnk');" ^
  "$s.TargetPath = '%INSTALL_ROOT%\Tools\TunerPro_CustomTools\Dashboard.exe';" ^
  "$s.WorkingDirectory = '%INSTALL_ROOT%\Tools\TunerPro_CustomTools';" ^
  "$s.Save()"

set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\TunerPro Tools Suite"
mkdir "%STARTMENU%" 2>nul
for %%F in ("%INSTALL_ROOT%\Tools\TunerPro_CustomTools\*.exe") do (
    powershell -NoProfile -Command ^
      "$s = (New-Object -COM WScript.Shell).CreateShortcut('%STARTMENU%\%%~nF.lnk');" ^
      "$s.TargetPath = '%%F';" ^
      "$s.WorkingDirectory = '%INSTALL_ROOT%\Tools\TunerPro_CustomTools';" ^
      "$s.Save()"
)

echo.
echo Installation terminee.
echo   - Executables : %INSTALL_ROOT%\Tools\TunerPro_CustomTools\
echo   - Voir TUNERPRO_SETUP.md pour configurer le menu Custom Tools de TunerPro.
echo   - Pour desinstaller : lancez uninstall_tunerpro_tools.bat
echo.

REM --- write the matching uninstaller next to this script ---
(
    echo @echo off
    echo echo Suppression de %INSTALL_ROOT% ...
    echo rmdir /s /q "%INSTALL_ROOT%"
    echo del "%%USERPROFILE%%\Desktop\TunerPro Tools Suite.lnk" 2^>nul
    echo rmdir /s /q "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\TunerPro Tools Suite" 2^>nul
    echo echo Desinstallation terminee.
) > uninstall_tunerpro_tools.bat

endlocal
