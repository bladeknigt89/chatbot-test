@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo === Local AI Chatbot telepito (Windows) ===
echo Elvart Python: 3.14

set "PYEXE="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.14 -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,14) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYEXE=py -3.14"
)
if not defined PYEXE (
  where python >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%V in ('python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2^>nul') do set "PYVER=%%V"
    if "!PYVER!"=="3.14" set "PYEXE=python"
  )
)
if not defined PYEXE (
  echo Python 3.14 nem talalhato.
  echo Telepitsd a Python 3.14-et: https://www.python.org/downloads/
  echo Windows-on a "py -3.14" inditonak PATH-on kell lennie.
  exit /b 1
)

echo Hasznalt Python: %PYEXE%
%PYEXE% -c "import sys; print(sys.version)"

where node >nul 2>&1
if errorlevel 1 (
  echo Node.js nem talalhato. Telepits Node.js 20+ LTS-t.
  exit /b 1
)

echo.
echo === Ollama telepites / inditas + modellek (models.json) ===
%PYEXE% scripts\install_ollama.py --models-json models.json
if errorlevel 1 (
  echo.
  echo FIGYELEM: Az Ollama telepitese, inditasa vagy a modell letoltes nem sikerult teljesen.
  echo Ha most telepult, zarj be minden terminalt, inditsd el az Ollama alkalmazast,
  echo majd futtasd ujra: install.bat
  echo.
  echo Folytatas a tobbi komponenssel...
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo .env letrehozva az .env.example alapjan.
)

if exist "backend\.venv\Scripts\python.exe" (
  backend\.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,14) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo A meglévő venv nem Python 3.14. Ujraepitom: backend\.venv
    rmdir /S /Q backend\.venv
  )
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo Python 3.14 venv letrehozasa...
  %PYEXE% -m venv backend\.venv
)

echo Python fuggosegek telepitese...
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
REM Natív csomagokhoz Python 3.14 wheel kötelező (ne forrásból fordítson PyO3-mal).
set "PIP_ONLY_BINARY=pydantic-core,orjson,pillow,numpy,greenlet,bcrypt,lxml,httptools,watchfiles,websockets"
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt
if errorlevel 1 exit /b 1
set "PIP_ONLY_BINARY="

echo Frontend fuggosegek telepitese...
pushd frontend
call npm install
if errorlevel 1 (
  popd
  exit /b 1
)
call npm run build
if errorlevel 1 (
  popd
  exit /b 1
)
popd

echo Adatbazis, admin felhasznalo, LLM modellek...
backend\.venv\Scripts\python.exe scripts\install_ollama.py --skip-install --models-json models.json
backend\.venv\Scripts\python.exe scripts\bootstrap.py
if errorlevel 1 (
  echo.
  echo A bootstrap / modell letoltes hibazott.
  echo Ellenorizd, hogy az Ollama fut-e, majd:
  echo   backend\.venv\Scripts\python.exe scripts\install_ollama.py --skip-install --models-json models.json
  echo   backend\.venv\Scripts\python.exe scripts\bootstrap.py
  echo Vagy Ollama nelkul (csak UI/API teszt):
  echo   backend\.venv\Scripts\python.exe scripts\bootstrap.py --skip-llm
  exit /b 1
)

backend\.venv\Scripts\python.exe scripts\make_sample_docs.py

echo.
echo Telepites kesz (Python 3.14).
echo Inditas: start.bat
echo Admin: http://localhost:8000  felhasznalo: ai  jelszo: No_comment_123
exit /b 0
