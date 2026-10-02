"""Webapp de demo · FIC III · Desafío 1 · Equipo SIMtec.

Envoltura del trabajo del repo: un recorrido de demo que no calcula nada (lee las salidas ya generadas),
el dashboard original del equipo tal cual, un navegador de resultados y un panel para recalcular en segundo plano.
Abrir con abrir_demo.bat.
"""
import sys

sys.dont_write_bytecode = True

import streamlit as st  # noqa: E402
from lib.datasets import selector

st.set_page_config(page_title="Retención de service Ranger · SIMtec", layout="wide")

st.markdown("""
<style>
  .block-container {padding-top: 2.2rem;}
  .tarjeta {background:#F3F3F3; border-radius:6px; padding:1.1rem 1.3rem; height:100%;}
  .tarjeta-oscura {background:#00095B; color:white; border-radius:6px; padding:1.1rem 1.3rem; height:100%;}
  .tarjeta-oscura * {color:white !important;}
  .numero {font-size:2.6rem; line-height:1.1; color:#1700F3; font-weight:300;}
  .tarjeta-oscura .numero {color:white;}
  .etiqueta {font-size:0.75rem; letter-spacing:0.15em; text-transform:uppercase; color:#1700F3; margin-bottom:0.4rem;}
  .tarjeta-oscura .etiqueta {color:#B9BCBD !important;}
  .paso {border-left:3px solid #1700F3; padding:0.2rem 0 0.2rem 0.9rem; margin-bottom:0.6rem;}
  .frase {font-size:1.6rem; text-align:center; color:#00095B; margin-top:1.2rem;}
  .frase b {color:#1700F3;}
</style>
""", unsafe_allow_html=True)

demo = [
    st.Page("paginas/inicio.py", title="Inicio", default=True),
    st.Page("paginas/bandeja.py", title="1 · Bandeja del concesionario"),
    st.Page("paginas/caso.py", title="2 · Caso guiado"),
    st.Page("paginas/resultados.py", title="3 · Resultados del modelo"),
]
explorar = [
    st.Page("paginas/lista.py", title="Lista completa"),
    st.Page("paginas/dashboard.py", title="Dashboard completo"),
    st.Page("paginas/evidencia.py", title="Evidencia y tablas"),
    st.Page("paginas/documentos.py", title="Documentos"),
]
operar = [st.Page("paginas/datasets.py", title="Datasets"),
          st.Page("paginas/corridas.py", title="Corridas (recalcular)")]

selector()
st.navigation({"Demo": demo, "Explorar": explorar, "Operar": operar}).run()
