"""Carga y selección de conjuntos de datos desde la demo."""
from datetime import date

import pandas as pd
import streamlit as st

from lib import corridas as C
from lib import datasets as D

st.title("Datasets")
st.write("Cargá un CSV de ventas y otro de agenda de servicios. Cada conjunto conserva sus propios datos, "
         "modelo, ranking y registros de ejecución.")
d = D.activo()
st.subheader(d["nombre"])
st.caption("Conjunto activo · corte de datos: " + d["cutoff"])
if C.pipeline_corrido():
    st.success("Este conjunto ya tiene resultados. Podés recorrer la demo o recalcularlos en Corridas.")
else:
    st.info("Todavía no hay resultados para este conjunto. Corré el Pipeline completo desde Corridas.")
st.page_link("paginas/corridas.py", label="Ir a Corridas")

if "archivos" in d:
    st.dataframe(pd.DataFrame([{"Archivo": tipo, "Nombre original": v["archivo"], "Filas": v["filas"],
                               "Desde": v["desde"], "Hasta": v["hasta"]}
                              for tipo, v in d["archivos"].items()]), hide_index=True, width="stretch")
    for tipo, info in d["archivos"].items():
        for columna, cantidad in info.get("identificadores_vacios", {}).items():
            if cantidad:
                st.warning(f"{tipo}: {cantidad:,} filas sin {columna}. Esas filas pueden quedar fuera del análisis.")

st.subheader("Cargar un nuevo conjunto")
st.caption("Los archivos pueden tener cualquier nombre. Deben ser CSV UTF-8, separados por comas, con las "
           "mismas columnas que los originales. Límite: 1 GB por archivo.")
with st.expander("Ver columnas necesarias"):
    for titulo, nombre in (("Ventas", D.VENTAS), ("Agenda de servicios", D.AGENDA)):
        st.write(titulo)
        st.code(", ".join(c for c in D._cabecera(D.original()["raw"] / nombre)
                          if c not in {"SalesType", "ScheduleModalityCode", "CancellationReason", "Quicklane"}))

with st.form("nuevo_dataset"):
    nombre = st.text_input("Nombre del conjunto", placeholder="Por ejemplo: Octubre 2026", max_chars=100)
    ventas = st.file_uploader("CSV de ventas", type=["csv"], key="csv_ventas")
    agenda = st.file_uploader("CSV de agenda de servicios", type=["csv"], key="csv_agenda")
    st.write("Fechas para el modelo")
    st.caption("El corte indica hasta cuándo los eventos están completos. Entrenamiento y calibración usan los "
               "períodos anteriores; la evaluación usa las ventanas posteriores que ya cerraron.")
    a, b, c = st.columns(3)
    train = a.date_input("Fin de entrenamiento", value=date(2025, 9, 30), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
    valid = b.date_input("Fin de calibración", value=date(2025, 12, 31), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
    cutoff = c.date_input("Corte de datos", value=date(2026, 8, 25), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
    enviado = st.form_submit_button("Validar y guardar", type="primary")
if enviado:
    try:
        with st.spinner("Validando archivos y guardando el conjunto…"):
            meta = D.guardar(nombre, ventas, agenda, cutoff, train, valid)
        st.session_state["dataset_guardado"] = meta["id"]
        st.success("Conjunto guardado. Seleccionalo para trabajar con sus datos.")
    except Exception as e:
        st.error(f"No se pudo guardar el conjunto: {e}")
if st.session_state.get("dataset_guardado"):
    if st.button("Usar el conjunto recién cargado", type="primary"):
        D.seleccionar(st.session_state["dataset_guardado"])
        # El selector lateral se inicializa con el conjunto elegido en la próxima ejecución.
        st.session_state.pop("selector_dataset", None)
        st.session_state.pop("dataset_guardado", None)
        st.rerun()

st.subheader("Conjuntos disponibles")
st.dataframe(pd.DataFrame([{"Conjunto": x["nombre"], "Corte": x["cutoff"],
                           "Resultados": "Disponibles" if (x["resultados"] / "data/processed/scores_actuales.parquet").exists()
                           else "Pendientes"} for x in D.catalogo()]), hide_index=True, width="stretch")
st.caption("Cambiá de conjunto desde Dataset activo, en el menú lateral. Volver al original recupera sus resultados.")
