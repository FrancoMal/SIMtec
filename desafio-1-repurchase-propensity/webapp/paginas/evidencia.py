"""Navegador de la evidencia ya generada: informes del análisis exploratorio, revisión cruzada, figuras y tablas.
Todo se lee de disco; no se calcula nada."""
import re
from pathlib import Path

import streamlit as st

from lib.fuentes import csv, etiqueta_fuente, rutas, texto

st.title("Evidencia y tablas")
etiqueta_fuente()
r = rutas()

TEMAS = {
    "01_taxonomia_target": "1 · Qué cuenta como retorno (taxonomía del evento)",
    "02_cadencia_ventana": "2 · Cadencia y ventana de mantenimiento",
    "03_retencion_churn": "3 · Retención y churn",
    "04_identidad_cliente_vehiculo": "4 · Identidad cliente–vehículo y flotas",
    "05_calidad_cobertura_leakage": "5 · Calidad, cobertura y leakage",
    "06_canal_dealer_experiencia": "6 · Canal, concesionario y experiencia",
}


def md_limpio(p: Path) -> str:
    """Markdown de los informes sin las imágenes con rutas relativas (las figuras se muestran aparte)."""
    if not p.exists():
        return "_Todavía no se generó: corré la tarea correspondiente desde **Corridas**._"
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "", texto(p))


t1, t2, t3, t4 = st.tabs(["Modelo", "Análisis exploratorio", "Revisión cruzada", "Todas las tablas"])

with t1:
    st.markdown(md_limpio(r["modelo"] / "resumen.md"))
    figs = sorted((r["figures"] / "modelo").glob("*.png")) if (r["figures"] / "modelo").exists() else []
    for i in range(0, len(figs), 2):
        cols = st.columns(2)
        for c, f in zip(cols, figs[i:i + 2]):
            c.image(str(f), caption=f.stem.replace("_", " "), width="stretch")

with t2:
    tema = st.selectbox("Tema", list(TEMAS), format_func=TEMAS.get)
    vista = st.radio("Ver", ["Informe", "Verificación independiente", "Figuras"], horizontal=True)
    if vista == "Figuras":
        figs = sorted((r["figures"] / "eda").glob(f"{tema}_*.png"))
        st.caption(f"{len(figs)} figuras" if figs else "Todavía no hay figuras: corré **Análisis exploratorio** "
                   "desde Corridas (~12 min).")
        for i in range(0, len(figs), 2):
            cols = st.columns(2)
            for c, f in zip(cols, figs[i:i + 2]):
                c.image(str(f), caption=f.stem.replace(tema + "_", "").replace("_", " "), width="stretch")
    else:
        p = r["reports"] / "eda" / (f"{tema}.md" if vista == "Informe" else f"{tema}_verificacion.md")
        st.markdown(md_limpio(p) if p.exists() else "_No hay archivo para este tema._")

with t3:
    archivos = sorted((r["reports"] / "revision_cruzada").glob("*.md"))
    a = st.selectbox("Documento", archivos, format_func=lambda p: p.stem.replace("_", " "))
    st.markdown(md_limpio(a))

with t4:
    tablas = sorted(r["reports"].rglob("*.csv")) if r["reports"].exists() else []
    filtro = st.text_input("Buscar tabla", placeholder="por ejemplo: lift, ventana, dealer, ablaciones")
    tablas = [p for p in tablas if filtro.lower() in p.name.lower()] if filtro else tablas
    st.caption(f"{len(tablas)} tablas")
    if tablas:
        p = st.selectbox("Tabla", tablas, format_func=lambda p: str(p.relative_to(r["reports"])))
        st.dataframe(csv(p), width="stretch", hide_index=True)
