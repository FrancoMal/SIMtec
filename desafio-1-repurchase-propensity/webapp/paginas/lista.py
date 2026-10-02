"""Lista completa de los vehículos scoreados del conjunto activo."""
import json

import streamlit as st

from lib.datasets import activo
from lib.fuentes import SALIDAS_PIPELINE, etiqueta_fuente, miles, pct, requiere, scores
from lib.listado import filtrar, tabla_completa

st.title("Lista completa · análisis inicial")
etiqueta_fuente()
requiere(*SALIDAS_PIPELINE)
s = scores()
params = json.loads(activo()["params"].read_text(encoding="utf8"))["segmentos"]
porcentajes = {"Alto": params["top_alto"], "Medio": params["top_medio"],
               "Bajo": 1 - params["top_alto"] - params["top_medio"]}
st.write("Todos los vehículos del ranking, incluidos los que ya tienen turno o no tienen concesionario asignado. "
         "La probabilidad indica el riesgo de no completar el mantenimiento en la red oficial.")
st.caption("Fecha = fecha de scoring. Los grupos se asignan por posición en el ranking: "
           f"Alto es el {pct(porcentajes['Alto'])} de mayor riesgo, Medio el siguiente {pct(porcentajes['Medio'])} "
           f"y Bajo el {pct(porcentajes['Bajo'])} restante. Estos porcentajes no son umbrales de probabilidad.")
st.page_link("paginas/contactos.py", label="Ver resultado de la segunda etapa: contactos priorizados")

resumen = st.columns(4)
resumen[0].metric("Vehículos totales", miles(len(s)))
for col, (grupo, porcentaje) in zip(resumen[1:], porcentajes.items()):
    col.metric(f"{grupo} · {pct(porcentaje)}", miles((s["segmento"] == grupo).sum()))

grupo = st.radio("Grupo de prioridad", ["Todos", "Alto", "Medio", "Bajo"], horizontal=True,
                 format_func=lambda g: "Todos · 100 %" if g == "Todos" else f"{g} · {pct(porcentajes[g])}",
                 key="lista_grupo")
buscar = st.text_input("Buscar por customer_id o vehicle_id", placeholder="Pegá un identificador completo o una parte",
                       key="lista_busqueda")
adicionales = st.toggle("Mostrar datos adicionales", value=False, key="lista_adicionales",
                        help="Prioridad, concesionario, fechas de mantenimiento, turno y aportes numéricos de SHAP.")
tabla = tabla_completa(s, adicionales)
vista = filtrar(tabla, grupo, buscar)
st.caption(f"{miles(len(vista))} de {miles(len(tabla))} vehículos · ordenados por riesgo de abandono (etapa 1)")
config = {
    "customer_id": st.column_config.TextColumn("customer_id"),
    "vehicle_id": st.column_config.TextColumn("vehicle_id"),
    "fecha": st.column_config.DateColumn("fecha", format="DD/MM/YYYY", help="Fecha en que se calculó el scoring"),
    "probabilidad": st.column_config.NumberColumn("probabilidad", min_value=0, max_value=1, format="%.4f"),
    "grupo": st.column_config.TextColumn("grupo"),
}
for i in (1, 2, 3):
    config[f"motivo_SHAP_{i}"] = st.column_config.TextColumn(f"motivo SHAP {i}", width="large")
    config[f"aporte_SHAP_{i}"] = st.column_config.NumberColumn(f"aporte SHAP {i}", format="%.4f",
                                                              help="Contribución en log-odds; no es una probabilidad")
st.dataframe(vista, column_config=config, hide_index=True, width="stretch", height=580)
if vista.empty:
    st.info("No hay vehículos que coincidan con esos filtros.")
st.caption("Los tres motivos son los que calculó SHAP para cada vehículo, ordenados por importancia absoluta. "
           "Incluyen factores que aumentan o reducen el riesgo; no se recalculan al filtrar.")
a, b = st.columns(2)
a.download_button("Descargar vista en CSV", vista.to_csv(index=False, float_format="%.8f").encode("utf-8-sig"),
                  file_name=f"ranking_{activo()['id']}_{grupo.lower()}.csv", mime="text/csv")
b.download_button("Descargar lista completa en CSV", tabla.to_csv(index=False, float_format="%.8f").encode("utf-8-sig"),
                  file_name=f"ranking_{activo()['id']}_completo.csv", mime="text/csv")
