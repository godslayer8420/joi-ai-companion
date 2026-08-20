@echo off
REM ── Aurion Voice Installer ──────────────────────────────────────────────────
REM Double-click this from Explorer, or run from any directory.
REM It automatically navigates to the repo and installs all 9 Aurion voices.

cd /d "%~dp0"
echo.
echo  Installing Aurion voices from: %~dp0
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START-AURION-INSTALL.ps1"
