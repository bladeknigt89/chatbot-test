@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Local AI Chatbot telepito (Windows) ===

where python >nul 2>&1
if errorlevel 1 (
  echo Python nem talalhato. Telepits Python 3.11+ verziot, es pipeld a PATH-ba.
  exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo Node.js nem talalhato. Telepits Node.js 20+ LTS-t.
  exit /b 1
)

echo.
echo === Ollama telepites / inditas + modellek (models.json) ===
python scripts\install_ollama.py --models-json models.json
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

if not exist "backend\.venv\Scripts\python.exe" (
  python -m venv backend\.venv
)

echo Python fuggosegek telepitese...
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt
if errorlevel 1 exit /b 1

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
echo Telepites kesz.
echo Inditas: start.bat
echo Admin: http://localhost:8000  felhasznalo: ai  jelszo: No_comment_123
exit /b 0
