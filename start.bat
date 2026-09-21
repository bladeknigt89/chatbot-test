@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo A virtuális környezet hiányzik. Futtasd: install.bat
  exit /b 1
)

backend\.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,14) else 1)" >nul 2>&1
if errorlevel 1 (
  echo A venv nem Python 3.14. Futtasd ujra: install.bat
  exit /b 1
)

backend\.venv\Scripts\python.exe scripts\start_all.py
exit /b %ERRORLEVEL%
