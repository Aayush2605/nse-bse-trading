@echo off
rem Double-click to start NSE BSE Trader. Close this window to stop it.
where py >nul 2>nul && (py -3 "%~dp0server.py" & goto :eof)
where python >nul 2>nul && (python "%~dp0server.py" & goto :eof)
echo Python 3.8 or newer is needed: install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH").
pause
