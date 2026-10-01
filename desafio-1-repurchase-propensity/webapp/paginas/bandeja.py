"""Paso 1 de la demo: la bandeja de UN concesionario, ya ordenada.

Se entra por concesionario a propósito: así la vista inicial muestra clientes con historia en un concesionario
oficial. Los vehículos que nunca pasaron por uno (sin concesionario asignado) quedan en el Dashboard completo:
no se esconden, pero no son el caso típico y en la primera fila confunden (100 % de riesgo, sin datos previos).
"""
import pandas as pd
import streamlit as st

from lib.fuentes import SALIDAS_PIPELINE, requiere, etiqueta_fuente, miles, pct, scores
from lib.motivos import motivo


def primera_oracion(s: str) -> str:
    return s.split(". ")[0].rstrip(".") + "."

DEMO_DEALER = "c1a39fba1bdf"  # el concesionario de la Ranger 2019 de la presentación
DEMO_VEHICULO = "e34f9e47700c8604"

st.title("La bandeja del concesionario")
etiqueta_fuente()
requiere(*SALIDAS_PIPELINE)
st.markdown("Esto es lo que ve un asesor de service al empezar el día: **su** lista de clientes en ventana, "
            "ordenada de mayor a menor riesgo de no volver, con el motivo principal de cada caso.")

s = scores()
s = s[s["last_maint_dealer"].notna()]
conteo = s["last_maint_dealer"].value_counts()
dealers = conteo.index.tolist()
idx = dealers.index(DEMO_DEALER) if DEMO_DEALER in dealers else 0

c1, c2, c3 = st.columns([2, 1, 1])
dealer = c1.selectbox("Concesionario (identificador seudonimizado)", dealers, index=idx,
                      format_func=lambda d: f"{d} · {miles(conteo[d])} vehículos")
sin_turno = c2.toggle("Ocultar los que ya tienen turno", value=True)
margen = c3.toggle("Sólo con 14 días de margen o más", value=True)

b = s[s["last_maint_dealer"] == dealer]
if sin_turno:
    b = b[~b["tiene_turno_agendado"]]
if margen:
    b = b[b["dias_restantes_horizonte"] >= 14]
b = b.sort_values("prob_churn", ascending=False).reset_index(drop=True)

k1, k2, k3 = st.columns(3)
k1.metric("Clientes en la lista", miles(len(b)))
k2.metric("En riesgo alto", miles((b["segmento"] == "Alto").sum()))
k3.metric("Se perderían si no se hace nada", miles(b["prob_churn"].sum()),
          help="Suma de las probabilidades: cuántos de estos clientes se espera que no vuelvan sin contacto.")

tabla = pd.DataFrame({
    "Prioridad": range(1, len(b) + 1),
    "Vehículo": b["vehicle_id"],
    "Riesgo de no volver": (b["prob_churn"] * 100).round(0),
    "Grupo": b["segmento"],
    "Motivo principal": [primera_oracion(motivo(f, t)) for f, t in zip(b["driver_1_feature"], b["driver_1"])],
    "Ranger": b["model_year"].fillna(0).astype(int).astype(str).replace("0", "—") + " · " + b["generation"].fillna(""),
    "Días de margen": b["dias_restantes_horizonte"],
})
pos = tabla.index[tabla["Vehículo"] == DEMO_VEHICULO]
st.caption("Elegí una fila para ver ese caso contado."
           + (f" Para la demo: la fila **{pos[0] + 1}**, vehículo {DEMO_VEHICULO} (la Ranger 2019 de la presentación)."
              if len(pos) else ""))
ev = st.dataframe(
    tabla, hide_index=True, width="stretch", height=430, on_select="rerun", selection_mode="single-row",
    column_config={
        "Riesgo de no volver": st.column_config.ProgressColumn(format="%d %%", min_value=0, max_value=100),
        "Motivo principal": st.column_config.TextColumn(width="large"),
    })

sel = ev.selection.rows if ev and ev.selection else []
if sel:
    vid = tabla.iloc[sel[0]]["Vehículo"]
    st.session_state["vehiculo"] = vid
    st.success(f"Elegido: **{vid}** · riesgo {int(tabla.iloc[sel[0]]['Riesgo de no volver'])} %")
if st.button("Ver el caso contado ➡️", type="primary"):
    st.switch_page("paginas/caso.py")
