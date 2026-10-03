#!/usr/bin/env bash
# Abre la aplicacion SIMtec con el entorno del proyecto (equivalente Linux/macOS de abrir_app.bat).
cd "$(dirname "$0")" || exit 1
export PYTHONIOENCODING=utf8
export PYTHONDONTWRITEBYTECODE=1
if [ ! -x "../.venv/bin/python" ]; then
    echo "No existe el entorno ../.venv. Ver README.md en la raiz del repo."
    exit 1
fi
echo "Aplicacion en http://localhost:8510 (Ctrl+C para detenerla)"
../.venv/bin/python -m streamlit run app.py
