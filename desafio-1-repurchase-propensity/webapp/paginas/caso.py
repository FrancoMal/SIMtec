"""Paso 2 de la demo: un vehículo contado en castellano, como la slide "Detrás de cada caso, una historia".
Los motivos son los mismos tres drivers que entrega el modelo, expresados en unidades de negocio."""
import pandas as pd
import streamlit as st

from lib.fuentes import SALIDAS_PIPELINE, requiere, etiqueta_fuente, miles, pct, scores
from lib.motivos import ACCION, motivo

DEMO_VEHICULO = "e34f9e47700c8604"  # la Ranger 2019 de la presentación

st.title("Detrás de cada caso, una historia")
etiqueta_fuente()
requiere(*SALIDAS_PIPELINE)

s = scores().set_index("vehicle_id")
vid = st.session_state.get("vehiculo", DEMO_VEHICULO)
if vid not in s.index:
    vid = DEMO_VEHICULO if DEMO_VEHICULO in s.index else (
        s[(s["segmento"] == "Alto") & s["last_maint_dealer"].notna()].sort_values("prob_churn").index[-1])
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
<p>Grupo <b>{seg}</b>. {ACCION.get(seg, '')}</p>
<p>Le quedan {num(r['dias_restantes_horizonte'])} días de margen.</p></div>""", unsafe_allow_html=True)

st.markdown('<div class="frase">El asesor no recibe un número: <b>recibe una conversación.</b></div>',
            unsafe_allow_html=True)

with st.expander("Ver cómo lo expresa el modelo (detalle técnico)"):
    st.markdown("Los tres motivos son los drivers del modelo (contribuciones SHAP) para este vehículo, tal como "
                "salen en el ranking:")
    for i in (1, 2, 3):
        st.code(r[f"driver_{i}"], language=None)

st.page_link("paginas/resultados.py", label="Siguiente: ¿funciona?", icon="➡️")
