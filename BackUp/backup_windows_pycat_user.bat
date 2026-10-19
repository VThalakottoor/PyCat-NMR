@echo off
setlocal EnableExtensions DisableDelayedExpansion
title PyCat - Windows backup

echo PyCat Windows backup
echo Copies new and changed files. Does not delete files from the backup.
echo Close PyCat before backing up its database.
echo.
echo Enter the full initial and final folder paths, for example E:\PyCat and C:\Backups\PyCat
set "PYCAT_SOURCE="
set /p "PYCAT_SOURCE=Initial folder (source): "
set "PYCAT_SOURCE=%PYCAT_SOURCE:"=%"
if not defined PYCAT_SOURCE goto missing_source
if not exist "%PYCAT_SOURCE%\." goto missing_source

echo.
set "PYCAT_DESTINATION="
set /p "PYCAT_DESTINATION=Final folder (destination): "
set "PYCAT_DESTINATION=%PYCAT_DESTINATION:"=%"
if not defined PYCAT_DESTINATION goto missing_destination

rem Reject identical or nested folders to avoid copying a backup into itself.
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; try { $s=[IO.Path]::GetFullPath($env:PYCAT_SOURCE).TrimEnd('\'); $d=[IO.Path]::GetFullPath($env:PYCAT_DESTINATION).TrimEnd('\'); $c=[StringComparison]::OrdinalIgnoreCase; if ($s.Equals($d,$c) -or $d.StartsWith($s+'\',$c) -or $s.StartsWith($d+'\',$c)) { Write-Host 'Error: source and backup must be separate folders, with neither inside the other.'; exit 1 } } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 goto failed

if not exist "%PYCAT_DESTINATION%\." mkdir "%PYCAT_DESTINATION%"
if not exist "%PYCAT_DESTINATION%\." goto failed

echo.
echo Source: "%PYCAT_SOURCE%"
echo Backup: "%PYCAT_DESTINATION%"
echo.
rem /E includes subfolders, including empty ones.
rem No /MIR, /PURGE, /MOV or /MOVE: source and backup files are not deleted.
rem /XJ skips directory junctions to avoid loops.
robocopy "%PYCAT_SOURCE%" "%PYCAT_DESTINATION%" /E /COPY:DAT /DCOPY:T /R:2 /W:2 /XJ
set "PYCAT_RESULT=%ERRORLEVEL%"
rem Robocopy exit codes 0 through 7 indicate successful copying or differences.
if %PYCAT_RESULT% GEQ 8 goto copy_failed

echo.
echo Backup complete. Files deleted from the source remain in the backup.
echo Changed source files replace their previous backup copies.
pause
exit /b 0

:missing_source
echo.
echo Error: enter an existing source folder, for example E:\PyCat.
echo Check that the source drive is connected and the folder path is correct.
pause
exit /b 1

:copy_failed
echo.
echo Backup failed or was incomplete. Robocopy exit code: %PYCAT_RESULT%
echo Review the messages above, fix the problem, and run this file again.
pause
exit /b %PYCAT_RESULT%

:missing_destination
echo.
echo Error: enter a final destination folder.
pause
exit /b 1

:failed
echo.
echo Backup could not start. Review the error above.
pause
exit /b 1
