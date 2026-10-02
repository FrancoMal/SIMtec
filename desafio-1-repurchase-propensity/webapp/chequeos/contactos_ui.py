"""Verificación de la segunda etapa en Streamlit AppTest, sin iniciar un servidor.

Usa las salidas locales originales y un catálogo temporal: no cambia el dataset
seleccionado por el usuario ni recalcula su pipeline.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

PROYECTO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROYECTO / "webapp"))
from lib import datasets as D  # noqa: E402
from lib import fuentes as F  # noqa: E402


def comprobar_app(app):
    assert not app.exception, [e.message for e in app.exception]


def comprobar_originales(tabla, scores):
    """Toda fila mostrada conserva exactamente la probabilidad y SHAP del vehículo."""
    fuente = scores.set_index("vehicle_id").loc[tabla["vehicle_id"]].reset_index()
    assert tabla["customer_id"].reset_index(drop=True).equals(fuente["customer_id"])
    assert tabla["probabilidad"].reset_index(drop=True).equals(fuente["prob_churn"])
    assert tabla["grupo"].astype("string").reset_index(drop=True).equals(fuente["segmento"].astype("string"))
    pd.testing.assert_series_equal(pd.to_datetime(tabla["fecha"]).reset_index(drop=True),
                                   pd.to_datetime(fuente["fecha_scoring"]).reset_index(drop=True),
                                   check_names=False, check_dtype=False)
    for n in (1, 2, 3):
        assert tabla[f"motivo_SHAP_{n}"].reset_index(drop=True).equals(fuente[f"driver_{n}"])


class GuardStop(Exception):
    pass


def comprobar_guardia(carpeta):
    """La lectura admite una entrega válida y corta antes de servir un scoring distinto."""
    processed = carpeta / "data" / "processed"
    processed.mkdir(parents=True)
    fuente = processed / "scores_actuales.parquet"
    fuente.write_bytes(b"scoring inicial de prueba")
    for nombre in ("contactos_por_cliente.parquet", "candidatos_contacto.parquet"):
        (processed / nombre).write_bytes(b"fixture: requiere verifica existencia, no contenido")
    resumen = processed / "contacto_resumen.json"
    resumen.write_text(json.dumps({"scores_sha256": hashlib.sha256(fuente.read_bytes()).hexdigest()}), encoding="utf8")
    with patch.object(F, "rutas", return_value={"raiz": carpeta, "processed": processed}), \
            patch.object(st, "warning") as warning, patch.object(st, "page_link"), \
            patch.object(st, "stop", side_effect=GuardStop):
        F.requiere_contactos()
        warning.assert_not_called()
        fuente.write_bytes(b"scoring nuevo: resultados de otro entrenamiento")
        F._huella.clear()
        try:
            F.requiere_contactos()
            raise AssertionError("La UI admitio una etapa 2 correspondiente a otro scoring")
        except GuardStop:
            assert "cambió" in warning.call_args.args[0]
        # Una entrega sin manifiesto todavía no terminó de publicarse.
        resumen.unlink()
        warning.reset_mock()
        try:
            F.requiere_contactos()
            raise AssertionError("La UI admitio artefactos incompletos")
        except GuardStop:
            assert "segunda etapa" in warning.call_args.args[0]
    print("Guardia de scoring obsoleto y entrega incompleta: OK", flush=True)


def main():
    from lib.resultados import filtrar_resultados, preparar_contactos
    from lib import corridas as C
    processed = PROYECTO / "data/processed"
    scores = pd.read_parquet(processed / "scores_actuales.parquet")
    clientes = pd.read_parquet(processed / "contactos_por_cliente.parquet")
    resumen = json.loads((processed / "contacto_resumen.json").read_text(encoding="utf8"))
    seleccion_path = D.CATALOGO / "seleccion.json"
    seleccion_antes = seleccion_path.read_bytes() if seleccion_path.exists() else None
    original = {**D.original(), "resultados": PROYECTO, "params": PROYECTO / "config" / "params.json"}

    with tempfile.TemporaryDirectory(prefix="simtec-contactos-ui-") as temporal:
        carpeta = Path(temporal).resolve()
        with patch.object(D, "CATALOGO", carpeta / "catalogo"), patch.object(D, "original", return_value=original):
            app = AppTest.from_file(str(PROYECTO / "webapp/demo.py"), default_timeout=60)
            app.session_state["dataset_id"] = "original"
            app.run()
            comprobar_app(app)
            assert app.selectbox(key="selector_dataset").value == "original"
            assert not app.sidebar.selectbox
            assert len(app.get("file_uploader")) == 2
            for pagina in ("datasets", "corridas", "contactos", "eficiencia"):
                app.switch_page(f"paginas/{pagina}.py").run()
                comprobar_app(app)
            app.switch_page("paginas/contactos.py").run()
            prefijo = "resultados_original_contactos"
            for estado, cantidad in [("Seleccionado", resumen["clientes_seleccionados"]),
                                     ("En espera", resumen["clientes_en_espera"]),
                                     ("Revisar", resumen["clientes_revisar"]),
                                     ("Todos", resumen["clientes_identificados"])]:
                app.selectbox(key=f"{prefijo}_situacion").set_value(estado).run()
                comprobar_app(app)
                tabla = app.dataframe[0].value
                assert len(tabla) == cantidad, (estado, len(tabla), cantidad)
                assert tabla.customer_id.is_unique
                comprobar_originales(tabla, scores)
            preparada = preparar_contactos(clientes)
            dealer = str(preparada.loc[preparada.concesionario.notna(), "concesionario"].iloc[0])
            app.selectbox(key=f"{prefijo}_grupo").set_value("Alto")
            app.selectbox(key=f"{prefijo}_dealer").set_value(dealer).run()
            comprobar_app(app)
            esperado = filtrar_resultados(preparada, grupo="Alto", concesionario=dealer)
            columnas_filtro = ["customer_id", "vehicle_id", "situacion", "concesionario", "grupo"]
            pd.testing.assert_frame_equal(app.dataframe[0].value[columnas_filtro], esperado[columnas_filtro])
            app.selectbox(key=f"{prefijo}_grupo").set_value("Todos")
            app.selectbox(key=f"{prefijo}_dealer").set_value("Todos").run()
            asociado = preparada[preparada.n_vehiculos_cliente.gt(1)].iloc[0]
            otro = next(v for v in asociado.vehiculos_cliente.split(" | ") if v != asociado.vehicle_id)
            app.text_input(key=f"{prefijo}_busqueda").set_value(otro).run()
            comprobar_app(app)
            assert app.dataframe[0].value.customer_id.tolist() == [asociado.customer_id]
            assert app.selectbox(key="resultados_original_cliente").value == str(asociado.customer_id)
            app.text_input(key=f"{prefijo}_busqueda").set_value("sin-coincidencias-test").run()
            comprobar_app(app)
            assert app.dataframe[0].value.empty
            app.text_input(key=f"{prefijo}_busqueda").set_value("").run()
            # El análisis inicial y la auditoría permanecen dentro de Resultados.
            tablas = [f.value for f in app.dataframe]
            assert any(len(t) == len(scores) and "customer_id" in t for t in tablas)
            assert any(len(t) == resumen["candidatos"] and "customer_id" in t for t in tablas)
            # Mientras una ejecución reescribe salidas, no se mezclan sus etapas.
            with patch.object(C, "activa", return_value={"dataset_id": "original"}):
                app.run()
                comprobar_app(app)
                assert any("ejecución en curso" in m.value for m in app.info)
                assert not app.dataframe
            app.run()
            comprobar_app(app)
            app.switch_page("paginas/eficiencia.py").run()
            comprobar_app(app)
            assert any(m.label == "ROC-AUC" for m in app.metric)
            assert app.get("plotly_chart")
            assert any("SHAP absoluto medio" in f.value for f in app.dataframe)
        comprobar_guardia(carpeta / "guardia")
    assert (seleccion_path.read_bytes() if seleccion_path.exists() else None) == seleccion_antes
    print("Cuatro secciones, filtros, detalle, SHAP, espera de ejecución y selección persistida: OK", flush=True)


if __name__ == "__main__":
    main()
