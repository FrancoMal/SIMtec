"""Dashboard del equipo con las rutas del dataset activo.
Se limpia la caché cuando cambia el conjunto o se recalculan los scores."""
import runpy
import sys

import streamlit as st

from lib.fuentes import REPO, SALIDAS_PIPELINE, etiqueta_fuente, mtime, requiere, rutas
from lib.datasets import activo

sys.dont_write_bytecode = True
etiqueta_fuente()
requiere(*SALIDAS_PIPELINE, "data/interim/agenda.parquet")

firma = (activo()["id"], mtime(rutas()["processed"] / "scores_actuales.parquet"))
if st.session_state.get("_firma_dashboard") != firma:
    st.cache_data.clear()
    st.session_state["_firma_dashboard"] = firma

st.info("Este es el tablero completo del equipo, con todos los filtros. Para la demo conviene empezar por la "
        "**Bandeja del concesionario**: acá las primeras filas son vehículos que nunca pasaron por un concesionario "
        "oficial (sin historia, por eso figuran con riesgo máximo y datos vacíos).")
# la configuración de página la define la webapp; la del dashboard se ignora para no pisarla
_spc = st.set_page_config
st.set_page_config = lambda *a, **k: None
try:
    runpy.run_path(str(REPO / "app" / "app.py"), run_name="__main__",
                   init_globals={"SIMTEC_DASHBOARD_RUTAS": rutas()})
finally:
    st.set_page_config = _spc
