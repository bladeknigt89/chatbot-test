@echo off
setlocal
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Elobb futtasd az install.bat fajlt.
  exit /b 1
)
backend\.venv\Scripts\python.exe scripts\start_all.py
