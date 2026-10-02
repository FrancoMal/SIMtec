"""Bandeja de clientes seleccionados por la segunda etapa."""
import streamlit as st

from lib.fuentes import contactos, requiere_contactos, etiqueta_fuente, miles
from lib.listado import tabla_contactos

DEMO_DEALER = "c1a39fba1bdf"

st.title("La bandeja del concesionario")
etiqueta_fuente()
requiere_contactos()
st.write("Clientes seleccionados por la segunda etapa, con un vehículo representativo por cliente. "
         "El orden combina oportunidad operativa y riesgo de abandono.")
s = contactos()
s = s[s["seleccionado"]].sort_values("orden_contacto")
conteo = s["last_maint_dealer"].value_counts()
dealers = conteo.index.tolist()
if not dealers:
    st.info("No hay clientes seleccionados para contactar en esta corrida. Consultá la lista y los motivos de revisión.")
    st.page_link("paginas/contactos.py", label="Ver contactos y auditoría")
    st.stop()
dealer = st.selectbox("Concesionario (identificador seudonimizado)", dealers,
                      index=dealers.index(DEMO_DEALER) if DEMO_DEALER in dealers else 0,
                      format_func=lambda d: f"{d} · {miles(conteo[d])} clientes")
b = s[s["last_maint_dealer"] == dealer]
k1, k2, k3 = st.columns(3)
k1.metric("Clientes seleccionados", miles(len(b)))
k2.metric("Representante en grupo Alto", miles((b["segmento"] == "Alto").sum()))
k3.metric("Vehículos Alto + Medio asociados", miles(b["n_vehiculos_cliente"].sum()))
st.caption("La probabilidad corresponde al riesgo de abandono; no mide la respuesta a una llamada. "
           "El orden es global para la corrida y puede tener saltos al filtrar por concesionario.")
tabla = tabla_contactos(b)
ev = st.dataframe(tabla, hide_index=True, width="stretch", height=480, on_select="rerun",
                  selection_mode="single-row", column_config={
                      "probabilidad": st.column_config.NumberColumn("probabilidad de abandono", format="%.4f"),
                      "motivos_operativos": st.column_config.TextColumn(width="large"),
                      "fecha": st.column_config.DateColumn(format="DD/MM/YYYY")})
sel = ev.selection.rows if ev and ev.selection else []
if sel:
    st.session_state["vehiculo"] = tabla.iloc[sel[0]]["vehicle_id"]
if st.button("Ver el caso contado", type="primary", disabled=tabla.empty):
    if not sel:
        st.session_state["vehiculo"] = tabla.iloc[0]["vehicle_id"]
    st.switch_page("paginas/caso.py")
st.page_link("paginas/contactos.py", label="Ver seleccionados, espera y auditoría de todos los concesionarios")
