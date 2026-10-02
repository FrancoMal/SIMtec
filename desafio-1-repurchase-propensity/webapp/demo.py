"""Aplicación de retención de service: datos, entrenamiento, resultados y eficiencia."""
import sys

sys.dont_write_bytecode = True

import streamlit as st
from lib import datasets as D
from lib import corridas as C
from lib.diseno import aplicar_estilo

st.set_page_config(page_title="SIMtec | Retención de service", layout="wide", initial_sidebar_state="collapsed")
aplicar_estilo()

# Las páginas solicitan cambios de conjunto antes de reconstruir el selector global.
pendiente = st.session_state.pop("_dataset_pendiente", None)
if pendiente:
    D.seleccionar(pendiente)
    st.session_state.pop("selector_dataset", None)
    st.session_state["_dataset_guardado_aviso"] = D.activo()["nombre"]

paginas = [
    st.Page("paginas/datasets.py", title="Carga de datos", default=True),
    st.Page("paginas/corridas.py", title="Entrenamiento"),
    st.Page("paginas/contactos.py", title="Resultados"),
    st.Page("paginas/eficiencia.py", title="Eficiencia del modelo"),
]
pagina = st.navigation(paginas, position="top")
marca, conjunto = st.columns([1.35, 1], vertical_alignment="center")
with marca:
    st.markdown('<div class="marca">SIMtec<span>Retención de service</span></div>', unsafe_allow_html=True)
with conjunto:
    D.selector()
st.divider()
ejecucion = C.activa()
if ejecucion and ejecucion.get("dataset_id", "original") == D.activo()["id"] and pagina.url_path in ("contactos", "eficiencia"):
    st.info("Hay una ejecución en curso para este conjunto. Los resultados estarán disponibles cuando termine.")
    st.page_link("paginas/corridas.py", label="Ver progreso del entrenamiento")

    @st.fragment(run_every=3)
    def esperar_resultados():
        if not C.activa():
            st.cache_data.clear()
            st.rerun(scope="app")

    esperar_resultados()
    st.stop()
pagina.run()
