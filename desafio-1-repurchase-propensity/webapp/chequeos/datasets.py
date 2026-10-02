r"""Chequeo de datasets sin levantar la demo ni reemplazar sus resultados.

Uso desde el proyecto: .venv\Scripts\python.exe webapp\chequeos\datasets.py
"""
from __future__ import annotations

import csv
import hashlib
import os
import subprocess
import sys
import tempfile
import shutil
from unittest.mock import patch
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

PROYECTO = Path(__file__).resolve().parents[2]
os.chdir(PROYECTO)
sys.path.insert(0, str(PROYECTO / "webapp"))
from lib import datasets as D  # noqa: E402
from lib import corridas as C  # noqa: E402


def huella(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def comprobar_app(app):
    assert not app.exception, [e.message for e in app.exception]


with tempfile.TemporaryDirectory(prefix="chequeo-datasets-", dir=PROYECTO / ".venv") as temporal:
    D.CATALOGO = Path(temporal) / "catalogo"
    original = D.original()
    protegidos = [original["raw"] / D.VENTAS, original["raw"] / D.AGENDA,
                  PROYECTO / "data/processed/scores_actuales.parquet",
                  PROYECTO / "data/models/metricas_test.csv"]
    antes = {p: huella(p) for p in protegidos}

    # Archivos incompletos, identificadores vacíos y fechas incorrectas no se aceptan.
    malo = Path(temporal) / "malo.csv"
    malo.write_text("vehicle_id\nv_1\n", encoding="utf8")
    try:
        D.validar_csv(malo, "ventas")
        raise AssertionError("Se aceptó un CSV sin columnas necesarias")
    except ValueError as e:
        assert "faltan columnas" in str(e)
    with (original["raw"] / D.VENTAS).open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames
        fila = next(lector)
    for campo, valor, esperado in (("SalesDate", "no-es-una-fecha", "fechas inválidas"),
                                   ("vehicle_id", "", "identificadores vacíos")):
        with malo.open("w", encoding="utf8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columnas)
            writer.writeheader()
            writer.writerow({**fila, campo: valor})
        try:
            D.validar_csv(malo, "ventas")
            raise AssertionError(f"Se aceptó un valor inválido en {campo}")
        except ValueError as e:
            assert esperado in str(e), str(e)
    print("Validación de CSV inválidos: OK", flush=True)

    # Carga con nombres libres, persistencia y selección sin resultados previos.
    with (original["raw"] / D.VENTAS).open("rb") as ventas, (original["raw"] / D.AGENDA).open("rb") as agenda:
        meta = D.guardar("Prueba de aislamiento", ventas, agenda, date(2026, 8, 25),
                         date(2025, 9, 30), date(2025, 12, 31))
    nuevo = next(d for d in D.catalogo() if d["id"] == meta["id"])
    assert nuevo["resultados"] != original["resultados"]
    assert meta["archivos"]["ventas"]["sha256"] == antes[original["raw"] / D.VENTAS]
    assert not (nuevo["resultados"] / "data/interim/sales.parquet").exists()

    # El lanzador registra el conjunto elegido y propaga las rutas al proceso hijo.
    C.CORRIDAS = Path(temporal) / "corridas"
    with patch.object(C, "dataset_activo", return_value=nuevo), patch.object(C.subprocess, "Popen") as lanzar, \
            patch.object(C, "_leer", return_value={"pid": os.getpid()}):
        C.lanzar("pipeline")
        entorno = lanzar.call_args.kwargs["env"]
        assert entorno["SIMTEC_OUTPUT_DIR"] == str(nuevo["resultados"])
        assert entorno["SIMTEC_DATASET"] == str(nuevo["raw"])
        assert entorno["SIMTEC_CUTOFF"] == nuevo["cutoff"]
    estado = next(C.CORRIDAS.glob("*/estado.json"))
    import json
    registro = json.loads(estado.read_text(encoding="utf8"))
    assert registro["dataset_id"] == meta["id"]
    registro.update(fin=registro["inicio"], codigo=0)
    estado.write_text(json.dumps(registro), encoding="utf8")

    app = AppTest.from_file(str(PROYECTO / "webapp/demo.py"), default_timeout=60).run()
    comprobar_app(app)
    app.switch_page("paginas/datasets.py").run()
    comprobar_app(app)
    app.selectbox(key="selector_dataset").select(meta["id"]).run()
    comprobar_app(app)
    assert app.session_state["dataset_id"] == meta["id"]
    app.switch_page("paginas/contactos.py").run()
    comprobar_app(app)
    assert any("Todavía no hay resultados" in w.value for w in app.warning)
    app.switch_page("paginas/corridas.py").run()
    comprobar_app(app)
    assert not any(b.label == "Comparar ahora" for b in app.button)
    app.switch_page("paginas/contactos.py").run()
    comprobar_app(app)
    assert any("Todavía no hay resultados" in w.value for w in app.warning)
    print("Carga, selección y ausencia de resultados mezclados: OK", flush=True)

    env = {**os.environ, "PYTHONPATH": str(PROYECTO / "src"), "PYTHONIOENCODING": "utf8", "MPLBACKEND": "Agg",
           "SIMTEC_DATASET": str(nuevo["raw"]), "SIMTEC_OUTPUT_DIR": str(nuevo["resultados"]),
           "SIMTEC_CUTOFF": nuevo["cutoff"]}
    if "--solo-ui" in sys.argv:
        # Reutiliza una copia de las salidas para revisar solo cambios de interfaz.
        for relativa in ("data/interim", "data/processed", "data/models", "reports/modelo", "reports/figures/modelo"):
            shutil.copytree(PROYECTO / relativa, nuevo["resultados"] / relativa)
    else:
        subprocess.run([sys.executable, "-u", "scripts/run_pipeline.py", "--config", str(nuevo["params"])],
                       env=env, cwd=PROYECTO, check=True, timeout=360)
    for nombre in ("metricas_test.csv", "capacidad_LightGBM_calibrado.csv"):
        esperado = pd.read_csv(PROYECTO / "data/models" / nombre)
        calculado = pd.read_csv(nuevo["resultados"] / "data/models" / nombre)
        pd.testing.assert_frame_equal(esperado, calculado, atol=1e-9, rtol=1e-9)
    print("Copia de resultados para prueba de interfaz: OK" if "--solo-ui" in sys.argv else
          "Pipeline aislado reproduce las métricas del original: OK", flush=True)

    # Ambas etapas pertenecen al dataset cargado; el hash enlaza el filtro con su scoring.
    processed = nuevo["resultados"] / "data/processed"
    contacto = json.loads((processed / "contacto_resumen.json").read_text(encoding="utf8"))
    assert contacto["scores_sha256"] == huella(processed / "scores_actuales.parquet")
    clientes = pd.read_parquet(processed / "contactos_por_cliente.parquet")
    assert clientes["customer_id"].is_unique
    assert int(clientes["seleccionado"].sum()) == contacto["clientes_seleccionados"]
    if "--solo-ui" not in sys.argv:
        tiempos = json.loads((nuevo["resultados"] / "reports/modelo/tiempos_pipeline.json").read_text(encoding="utf8"))
        assert tiempos["estado"] == "completo"
        assert Path(tiempos["dataset_raw"]) == nuevo["raw"]
        assert Path(tiempos["resultados"]) == nuevo["resultados"]
        assert tiempos["segundos_total"] > 0
        assert all(e["segundos"] >= 0 for e in tiempos["etapas"])
        print("Tiempos reales por etapa, asociados al conjunto correcto: OK", flush=True)
    for pagina in ("paginas/datasets.py", "paginas/corridas.py", "paginas/contactos.py", "paginas/eficiencia.py"):
        app.switch_page(pagina).run()
        comprobar_app(app)
    app.switch_page("paginas/contactos.py").run()
    st.cache_data.clear()
    with patch("pandas.read_parquet", wraps=pd.read_parquet) as lecturas:
        app.switch_page("paginas/contactos.py").run()
        comprobar_app(app)
        assert lecturas.called
        assert all(Path(llamada.args[0]).is_relative_to(nuevo["resultados"]) for llamada in lecturas.call_args_list)
    app.selectbox(key="selector_dataset").select("original").run()
    comprobar_app(app)
    assert app.session_state["dataset_id"] == "original"
    app.switch_page("paginas/contactos.py").run()
    comprobar_app(app)
    print("Páginas del conjunto nuevo y vuelta al original: OK", flush=True)
    assert {p: huella(p) for p in protegidos} == antes
    print("CSV y resultados originales intactos: OK", flush=True)
