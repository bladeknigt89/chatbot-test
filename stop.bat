@echo off
setlocal
cd /d "%~dp0"
if exist "backend\.venv\Scripts\python.exe" (
  backend\.venv\Scripts\python.exe scripts\stop_all.py
) else (
  echo Nincs virtualis kornyezet.
)
