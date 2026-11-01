@echo off
rem Double-click to start NSE BSE Trader. Keep this window open while you use it; close it to stop.
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo Python 3.8 or newer is needed. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" in the installer, then double-click this file again.
  pause
  exit /b 1
)
echo Starting NSE BSE Trader with %PY% ...
%PY% server.py
echo.
echo The app stopped. If you see an error above, send a screenshot of this window.
pause
