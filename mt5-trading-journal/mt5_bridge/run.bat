@echo off
REM Quick manual start — double-click this or call it from a shortcut.
REM For auto-start on login, run install_service.ps1 instead.

cd /d "%~dp0"
echo Starting MT5 Journal Bridge...
python bridge.py
pause
