#!/usr/bin/env bash
# FIC III - Desafio 1 - SIMtec (equivalente Linux/macOS de ejecutar.bat)
cd "$(dirname "$0")" || exit 1

export PYTHONIOENCODING=utf8
export PYTHONPATH=src
PY=.venv/bin/python
ARG="$1"

pausa() { [ -z "$ARG" ] && read -r -p "Presiona Enter para continuar..." _; }

if [ ! -x "$PY" ]; then
    echo "No existe el entorno .venv. Crealo una vez con:"
    echo "   uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt"
    echo "o con:"
    echo "   python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
    pausa
    exit 1
fi

# Uso directo sin menu: ./ejecutar.sh pipeline | notebooks | informe | diccionario | complementarios | dashboard | todo | resumen
menu() {
    echo
    echo " =========================================================="
    echo "  FIC III - Desafio 1 - Repurchase / retencion de service"
    echo " =========================================================="
    echo "  1. Pipeline completo (CSV -> ventanas -> features -> modelo -> scoring)   ~3 min"
    echo "  2. Notebooks de evidencia (generar y ejecutar)"
    echo "  3. Informe oficial (docx sobre el template de Ford + PDF, usa LibreOffice)"
    echo "  4. Diccionario del dataset analitico"
    echo "  5. Dashboard (Streamlit, abre en el navegador)"
    echo "  6. Todo en orden: 1, 2, 4, 3"
    echo "  7. Analisis complementarios (sensibilidad de ventana + ablaciones)   ~15 min"
    echo "  8. Solo ver el resumen de las salidas actuales (sin correr nada)"
    echo "  0. Salir"
    echo
    read -r -p "Opcion: " OPCION
    [ "$OPCION" = "0" ] && exit 0
}

# los CSV crudos vienen por Git LFS: si sólo está el puntero, el pipeline no tiene datos
datos_ok() {
    local dir="${SIMTEC_DATASET:-../Dataset}" f
    for f in "$dir/ranger_sales_arg_2024_2026.csv" "$dir/ranger_service_agenda_arg_2024_2026 1.csv"; do
        if [ ! -f "$f" ]; then
            echo " Falta $f (o definir SIMTEC_DATASET con la carpeta de los CSV)."; return 1
        fi
        if head -c 40 "$f" | grep -q "git-lfs"; then
            echo " $f es sólo el puntero de Git LFS. Bajar los datos con:"
            echo "    sudo apt install git-lfs && git lfs install && git lfs pull"
            return 1
        fi
    done
}

# el PDF del informe se exporta con LibreOffice (en Windows lo hace Word)
libreoffice_ok() {
    if ! command -v soffice >/dev/null; then
        echo " Falta LibreOffice para exportar el PDF: sudo apt install libreoffice-writer python3-uno"; return 1
    fi
}

# corre un script; si falla muestra el estado de las salidas y termina
paso() {
    HECHO=1
    echo
    echo " ---- $1 ----"
    if ! "$PY" "$2"; then
        echo
        echo " ERROR en \"$1\". Revisar el mensaje de arriba. Estado de las salidas:"
        "$PY" scripts/resumen_salidas.py "$OPCION"
        pausa
        exit 1
    fi
}

while true; do
    if [ -n "$ARG" ]; then OPCION="$ARG"; else menu; fi

    case "${OPCION,,}" in
        1) OPCION=pipeline ;;
        2) OPCION=notebooks ;;
        3) OPCION=informe ;;
        4) OPCION=diccionario ;;
        5) OPCION=dashboard ;;
        6) OPCION=todo ;;
        7) OPCION=complementarios ;;
        8) OPCION=resumen ;;
        *) OPCION="${OPCION,,}" ;;
    esac

    case "$OPCION" in
        pipeline|todo|complementarios) datos_ok || { pausa; exit 1; } ;;
    esac
    case "$OPCION" in
        informe|todo) libreoffice_ok || { pausa; exit 1; } ;;
    esac

    # marca de inicio (segundos epoch) para que el resumen distinga lo generado ahora de lo viejo
    "$PY" scripts/resumen_salidas.py --inicio
    HECHO=

    case "$OPCION" in
        pipeline)    paso "Pipeline completo" scripts/run_pipeline.py ;;
        notebooks)   paso "Notebooks" scripts/build_notebooks.py ;;
        informe)     paso "Informe docx + PDF" scripts/build_informe_docx.py ;;
        diccionario) paso "Diccionario del dataset" scripts/diccionario_dataset.py ;;
        complementarios)
            paso "Sensibilidad de ventana" scripts/sensibilidad_ventana.py
            paso "Ablaciones" scripts/ablaciones.py
            ;;
        todo)
            paso "Pipeline completo" scripts/run_pipeline.py
            paso "Notebooks" scripts/build_notebooks.py
            paso "Diccionario del dataset" scripts/diccionario_dataset.py
            paso "Informe docx + PDF" scripts/build_informe_docx.py
            ;;
        dashboard)
            echo
            echo " Abriendo la aplicacion web (http://localhost:8510). Ctrl+C para detenerlo."
            (cd webapp && "../$PY" -m streamlit run app.py)
            pausa
            exit 0
            ;;
        resumen)
            for o in pipeline notebooks diccionario informe; do
                "$PY" scripts/resumen_salidas.py "$o" --sin-inicio
            done
            pausa
            exit 0
            ;;
    esac

    if [ -z "$HECHO" ]; then
        echo "Opcion no reconocida: $OPCION"
        [ -n "$ARG" ] && exit 1
        continue
    fi
    break
done

# cuadro resumen de lo que produjo esta corrida
"$PY" scripts/resumen_salidas.py "$OPCION"

pausa
exit 0
