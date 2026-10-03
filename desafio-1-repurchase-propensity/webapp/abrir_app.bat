@echo off
rem Abre la aplicacion SIMtec con el entorno del proyecto.
cd /d "%~dp0"
set PYTHONIOENCODING=utf8
set PYTHONDONTWRITEBYTECODE=1
if not exist "..\.venv\Scripts\python.exe" (
    echo No existe el entorno ..\.venv. Ver README.md en la raiz del repo.
    pause
    exit /b 1
)
start "" http://localhost:8510
"..\.venv\Scripts\python.exe" -m streamlit run app.py
