@echo off
setlocal EnableExtensions DisableDelayedExpansion
title PyCat - Windows mirror backup

echo PyCat Windows mirror backup
echo Makes the backup match the source PyCat folder.
echo Files and folders present ONLY in the backup will be DELETED.
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
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; try { $s=[IO.Path]::GetFullPath($env:PYCAT_SOURCE).TrimEnd('\'); $d=[IO.Path]::GetFullPath($env:PYCAT_DESTINATION).TrimEnd('\'); $c=[StringComparison]::OrdinalIgnoreCase; if ($s.Equals([IO.Path]::GetPathRoot($s).TrimEnd('\'),$c) -or $d.Equals([IO.Path]::GetPathRoot($d).TrimEnd('\'),$c)) { Write-Host 'Error: select a PyCat folder, not a drive root.'; exit 1 }; if ($s.Equals($d,$c) -or $d.StartsWith($s+'\',$c) -or $s.StartsWith($d+'\',$c)) { Write-Host 'Error: source and backup must be separate folders, with neither inside the other.'; exit 1 } } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 goto failed

if not exist "%PYCAT_DESTINATION%\." mkdir "%PYCAT_DESTINATION%"
if not exist "%PYCAT_DESTINATION%\." goto failed

echo.
echo Source: "%PYCAT_SOURCE%"
echo Backup: "%PYCAT_DESTINATION%"
echo.
echo WARNING: destination-only files and folders will be permanently deleted.
choice /C YN /N /M "Continue with this mirror backup? [Y/N] "
if errorlevel 2 goto cancelled
if errorlevel 1 goto run_mirror
goto failed

:run_mirror
rem /MIR copies the directory tree and removes destination-only items.
rem /IS /IT also recopy equal-size/time files to keep their actual content in sync.
rem /XJ skips directory junctions to avoid loops.
robocopy "%PYCAT_SOURCE%" "%PYCAT_DESTINATION%" /MIR /COPY:DAT /DCOPY:T /R:2 /W:2 /XJ /IS /IT
set "PYCAT_RESULT=%ERRORLEVEL%"
rem Robocopy exit codes 0 through 7 indicate successful copying or differences.
if %PYCAT_RESULT% GEQ 8 goto copy_failed

echo.
echo Mirror backup complete. The backup now matches the source PyCat folder.
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

:cancelled
echo.
echo Mirror cancelled. No files were copied or deleted.
pause
exit /b 0
