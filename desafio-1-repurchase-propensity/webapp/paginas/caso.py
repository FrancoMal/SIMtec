"""Paso 2 de la demo: un vehículo contado en castellano, como la slide "Detrás de cada caso, una historia".
Los motivos son los mismos tres drivers que entrega el modelo, expresados en unidades de negocio."""
import pandas as pd
import streamlit as st

from lib.fuentes import SALIDAS_PIPELINE, requiere, etiqueta_fuente, miles, pct, scores, requiere_contactos, contactos
from lib.motivos import motivo

DEMO_VEHICULO = "e34f9e47700c8604"  # la Ranger 2019 de la presentación

st.title("Detrás de cada caso, una historia")
etiqueta_fuente()
requiere(*SALIDAS_PIPELINE)

s = scores().set_index("vehicle_id")
if s.empty:
    st.info("Este conjunto no tiene vehículos en la ventana actual de mantenimiento.")
    st.stop()
vid = st.session_state.get("vehiculo", DEMO_VEHICULO)
if vid not in s.index:
    candidatos = s[(s["segmento"] == "Alto") & s["last_maint_dealer"].notna()]
    vid = DEMO_VEHICULO if DEMO_VEHICULO in s.index else (
        candidatos.sort_values("prob_churn").index[-1] if not candidatos.empty else s.index[0])
otro = st.text_input("Vehículo", value=vid, help="Se elige desde la bandeja, o se puede pegar un identificador.")
if otro.strip() in s.index:
    vid = otro.strip()
    st.session_state["vehiculo"] = vid
elif otro.strip() != vid:
    st.error("No encuentro ese vehículo en la lista de hoy.")
r = s.loc[vid]


def num(x, dec=0):
    return "—" if pd.isna(x) else f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


anio = "" if pd.isna(r["model_year"]) else f" {int(r['model_year'])}"
flota = r["fleet_size_sales"]
quien = ("una flota de " + num(flota) + " vehículos") if pd.notna(flota) and flota > 1 else "un cliente particular"
n_serv = int(r["n_maint"]) if pd.notna(r["n_maint"]) else 0
datos = [f"{num(r['vehicle_age_years'])} años de uso"]
if pd.notna(r["km_per_year"]):
    datos.append(f"unos {num(r['km_per_year'])} km por año")
datos.append(f"{n_serv} service{'s' if n_serv != 1 else ''} en un concesionario oficial" if n_serv
             else "todavía no hizo ningún service en un concesionario oficial")
datos.append(f"es {quien}")

c1, c2, c3 = st.columns(3, gap="medium")
c1.markdown(f"""<div class="tarjeta"><div class="etiqueta">Este es el cliente</div>
<div class="numero" style="color:#00095B">Ranger{anio}</div>
<p>{r['generation'] if pd.notna(r['generation']) else ''}</p>
<ul>{''.join(f'<li>{d}</li>' for d in datos)}</ul></div>""", unsafe_allow_html=True)

motivos = [motivo(r[f"driver_{i}_feature"], r[f"driver_{i}"]) for i in (1, 2, 3)]
c2.markdown('<div class="tarjeta" style="background:white;border:1px solid #B9BCBD">'
            '<div class="etiqueta">Lo que cuentan sus datos</div>'
            + "".join(f"<p><b style='color:#1700F3'>{i}.</b> {m}</p>" for i, m in enumerate(motivos, 1)) + "</div>",
            unsafe_allow_html=True)

seg = r["segmento"]
c3.markdown(f"""<div class="tarjeta-oscura"><div class="etiqueta">Lo que pasa ahora</div>
<div class="numero">{pct(r['prob_churn'])}</div>
<p>de probabilidad de no volver al service en un concesionario oficial.</p>
<p>Grupo original <b>{seg}</b>.</p>
<p>Le quedan {num(r['dias_restantes_horizonte'])} días de margen.</p></div>""", unsafe_allow_html=True)

st.subheader("Decisión de la segunda etapa")
requiere_contactos()
candidato = contactos(candidatos=True)
candidato = candidato[candidato["vehicle_id"] == vid]
if candidato.empty:
    st.info("Este vehículo pertenece al grupo Bajo y no entra en la segunda etapa.")
else:
    c = candidato.iloc[0]
    situacion = "Seleccionado" if c["seleccionado"] else "En espera" if c["en_espera"] else c["estado_contacto"]
    st.write(f"**{situacion}** · {c['motivos_operativos']}")
    if not c["representante"] and c["estado_contacto"] != "Sin identificador":
        st.caption("Otro vehículo representa a este cliente en la lista consolidada. Consultá sus vehículos asociados.")
    st.caption(f"Vehículos del cliente en Alto + Medio: {c['vehiculos_cliente']}")

with st.expander("Ver cómo lo expresa el modelo (detalle técnico)"):
    st.markdown("Los tres motivos son los drivers del modelo (contribuciones SHAP) para este vehículo, tal como "
                "salen en el ranking:")
    for i in (1, 2, 3):
        st.code(r[f"driver_{i}"], language=None)

st.page_link("paginas/resultados.py", label="Siguiente: ¿funciona?")
