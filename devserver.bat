@echo off
REM Run the PowerShell dev server script with ExecutionPolicy Bypass so Windows users can start it without changing system policy
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0devserver.ps1" -Port 8080
