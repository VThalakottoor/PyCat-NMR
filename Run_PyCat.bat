@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0" || goto :failed

set "PYCAT_APP=PyCat_NMR.py"
if not exist "%PYCAT_APP%" set "PYCAT_APP=PyCat_NMR(7).py"
if not exist "%PYCAT_APP%" goto :missing_files
if not exist "requirements.txt" goto :missing_files

set "VENV=%USERPROFILE%\venv\pycat"
if not exist "%VENV%" if exist "%USERPROFILE%\venvs\pycat\Scripts\python.exe" set "VENV=%USERPROFILE%\venvs\pycat"
set "VENV_PYTHON=%VENV%\Scripts\python.exe"
set "VERSION_CHECK=import sys; raise SystemExit(sys.version_info < (3, 9))"

if exist "%VENV_PYTHON%" goto :check_venv
py -3 -c "%VERSION_CHECK%" >nul 2>&1
if errorlevel 1 goto :try_python
py -3 -m venv "%VENV%" || goto :setup_failed
goto :check_venv

:try_python
python -c "%VERSION_CHECK%" >nul 2>&1
if errorlevel 1 (
    echo Install Python 3.9 or newer with Tcl/Tk support, then run this launcher again.
    goto :setup_failed
)
python -m venv "%VENV%" || goto :setup_failed

:check_venv
"%VENV_PYTHON%" -c "%VERSION_CHECK%" || goto :bad_venv
"%VENV_PYTHON%" -c "import tkinter" || goto :missing_tk

set "INSTALLED_REQUIREMENTS=%VENV%\.pycat-requirements.txt"
if /i "%~1"=="--install" goto :install
if not exist "%INSTALLED_REQUIREMENTS%" goto :install
fc /b "requirements.txt" "%INSTALLED_REQUIREMENTS%" >nul 2>&1
if errorlevel 1 goto :install
goto :launch

:install
echo Installing PyCat Python dependencies...
"%VENV_PYTHON%" -m pip install -r "requirements.txt" || goto :setup_failed
copy /y /b "requirements.txt" "%INSTALLED_REQUIREMENTS%" >nul || goto :setup_failed

:launch
"%VENV_PYTHON%" "%PYCAT_APP%"
if errorlevel 1 goto :unwind_failed
popd
exit /b 0

:missing_files
echo Place this launcher, requirements.txt, and PyCat_NMR.py in the same folder.
goto :unwind_failed

:bad_venv
echo Use Python 3.9 or newer for the PyCat environment at "%VENV%".
goto :setup_failed

:missing_tk
echo Install or repair Python with Tcl/Tk support enabled.
goto :setup_failed

:setup_failed
echo PyCat setup could not finish.
:unwind_failed
popd
:failed
pause
exit /b 1
