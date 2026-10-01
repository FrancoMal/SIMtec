@echo off
rem Abre la webapp de demo en http://localhost:8510 (usa el entorno .venv del proyecto, una carpeta arriba).
cd /d "%~dp0"
set PYTHONIOENCODING=utf8
set PYTHONDONTWRITEBYTECODE=1
if not exist "..\.venv\Scripts\python.exe" (
    echo No existe el entorno ..\.venv. Ver EMPEZAR_ACA.md en la raiz del repo, paso 3.
    pause
    exit /b 1
)
start "" http://localhost:8510
"..\.venv\Scripts\python.exe" -m streamlit run demo.py
