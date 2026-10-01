"""Paso 3 de la demo: ¿funciona? Las mismas tres ideas de la presentación (slides 10 a 12), leídas de las salidas."""
import plotly.graph_objects as go
import streamlit as st

from lib.fuentes import SALIDAS_PIPELINE, requiere, csv, etiqueta_fuente, miles, pct, rutas
from lib.metricas import kpis

st.title("El mismo esfuerzo, el doble de resultado")
etiqueta_fuente()
requiere(*SALIDAS_PIPELINE)
k = kpis()
r = rutas()
st.markdown(f"Lo probamos como se usaría de verdad: el modelo se entrenó con datos hasta el {k['train_end'][8:10]}/"
            f"{k['train_end'][5:7]}/{k['train_end'][:4]} y se evaluó en {miles(k['n_test'])} ventanas de enero a marzo "
            f"de 2026, meses que nunca había visto.")

izq, der = st.columns([3, 2], gap="large")
with izq:
    st.markdown("**De cada 10 contactos, cuántos llegan a un cliente que estaba dejando Ford**")
    fig = go.Figure(go.Bar(
        x=["Hoy (a todos igual)", "Con nuestra solución (el 20 % de mayor riesgo)"],
        y=[k["base"] * 10, k["prec20"] * 10], marker_color=["#B9BCBD", "#1700F3"],
        text=[f"{round(k['base'] * 10)} de 10", f"{round(k['prec20'] * 10)} de 10"], textposition="outside",
        textfont=dict(size=22, color="#00095B"), hovertemplate="%{y:.1f} de 10<extra></extra>"))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0, 10], visible=False),
                      plot_bgcolor="white", paper_bgcolor="white", font=dict(color="#00095B", size=14))
    st.plotly_chart(fig, width="stretch")
with der:
    st.markdown(f"""<div class="tarjeta"><div class="numero">{round(k['decil1'] * 10)} de cada 10</div>
de los clientes que nuestra solución pone primeros (el 10 % de mayor riesgo) estaban dejando Ford.</div>""",
                unsafe_allow_html=True)
    st.write("")
    st.markdown(f"""<div class="tarjeta"><div class="numero">2 de cada 3</div>
clientes que están por dejar Ford reciben un contacto a tiempo ({pct(k['recall_mes'])}), con
{miles(k['contactos_mes'])} contactos por mes entre todos los concesionarios.</div>""", unsafe_allow_html=True)

st.subheader("La evidencia: probado en meses que nunca vio")
a, b = st.columns(2, gap="large")
a.markdown("**¿A cuántos de los que se van llegamos, según cuántos contactamos?**")
a.image(str(r["figures"] / "modelo" / "ganancia.png"), width="stretch")
a.caption(f"Con el 20 % de los contactos se llega al {pct(k['recall20'])} de los que se van; sin orden, al 20 %. "
          "La línea gris es contactar sin orden, como hoy.")
b.markdown("**Cuando dice 70 %, ¿se van 7 de cada 10?**")
b.image(str(r["figures"] / "modelo" / "calibracion.png"), width="stretch")
b.caption(f"Sí: la probabilidad declarada coincide con lo que después pasa (error de calibración {k['ece']:.3f}"
          .replace(".", ",") + "). Eso permite planificar la capacidad de contacto.")

st.subheader("Un resultado que se puede sostener")
if not (r["modelo"] / "ablaciones.csv").exists():
    st.info("Esta parte sale de las **Ablaciones**: correlas desde *Corridas* (~1,5 min) para verla.", icon="⏳")
    st.stop()
ab = csv(r["modelo"] / "ablaciones.csv")
base = float(ab.loc[ab["variante"].str.startswith("base"), "roc_auc"].iloc[0])
km = float(ab.loc[ab["variante"].str.contains("KM"), "roc_auc"].iloc[0])
x, y = st.columns([2, 3], gap="large")
with x:
    fig = go.Figure(go.Bar(x=["Con dos datos que “miraban el futuro”", "Sin ellos: lo que se sostiene"],
                           y=[km, base], marker_color=["#B9BCBD", "#1700F3"],
                           text=[f"{km:.2f}".replace(".", ","), f"{base:.2f}".replace(".", ",")], textposition="outside",
                           textfont=dict(size=22, color="#00095B"), hoverinfo="skip"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0.5, 0.9], visible=False),
                      plot_bgcolor="white", paper_bgcolor="white", font=dict(color="#00095B", size=13))
    st.plotly_chart(fig, width="stretch")
    st.caption("Calidad del orden: 0,5 = al azar · 1 = perfecto.")
with y:
    st.markdown(
        "Dos columnas del dataset son valores del día en que se extrajeron los datos, no de cada fecha: son fotos de "
        "hoy mezcladas con el pasado. Con ellas el modelo parecía mejor, pero esa información no existe cuando hay que "
        f"decidir a quién contactar.\n\n**Las sacamos. {base:.2f} es lo que se puede prometer y cumplir.**".replace("0.", "0,"))
    st.markdown(f"Además, las variantes que quitan grupos de variables quedan casi igual: el resultado no depende de "
                "ninguna pieza en particular (detalle en *Evidencia y tablas*).")

with st.expander("Ver la tabla completa de métricas (detalle técnico)"):
    met = csv(r["models"] / "metricas_test.csv")
    st.dataframe(met.round(3), hide_index=True, width="stretch")
    st.dataframe(ab[["variante", "roc_auc", "pr_auc", "ece", "nota"]], hide_index=True, width="stretch")
