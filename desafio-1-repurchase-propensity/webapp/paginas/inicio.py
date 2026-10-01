import streamlit as st

from lib.fuentes import SALIDAS_PIPELINE, requiere, etiqueta_fuente, miles, pct, scores
from lib.metricas import kpis

st.markdown('<div class="etiqueta">Ford Innovation Challenge III · Desafío 1 · Equipo SIMtec</div>', unsafe_allow_html=True)
st.title("A quién contactar primero para que la Ranger vuelva al service")
etiqueta_fuente()
requiere(*SALIDAS_PIPELINE)

k = kpis()
s = scores()
st.markdown(
    f"Cada mes, entre 6.000 y 7.000 Ranger entran en su ventana de service y **cuatro de cada diez no vuelven a un "
    f"concesionario oficial**. Esta solución ordena la lista para que el contacto llegue primero a quien se está yendo, "
    f"y explica por qué. Hoy la lista tiene **{miles(len(s))} vehículos**.")

c1, c2, c3 = st.columns(3)
c1.markdown(f"""<div class="tarjeta"><div class="etiqueta">Cada contacto rinde el doble</div>
<div class="numero">{round(k['prec20'] * 10)} de 10</div>
contactos al 20 % de mayor riesgo llegan a alguien que se estaba yendo. Hoy, sin orden, son {round(k['base'] * 10)} de 10.</div>""",
            unsafe_allow_html=True)
c2.markdown(f"""<div class="tarjeta"><div class="etiqueta">Llega a tiempo</div>
<div class="numero">{pct(k['recall_mes'])}</div>
de los que se van reciben un contacto, con {miles(k['contactos_mes'])} contactos por mes entre todos los concesionarios.</div>""",
            unsafe_allow_html=True)
c3.markdown(f"""<div class="tarjeta"><div class="etiqueta">Probado en meses que no vio</div>
<div class="numero">{miles(k['n_test'])}</div>
ventanas de enero a marzo de 2026, con un modelo entrenado sólo con datos hasta septiembre de 2025.</div>""",
            unsafe_allow_html=True)

st.subheader("Recorrido de la demo")
st.caption("Tres pasos, sin correr nada: todo se lee de los resultados ya generados.")
pasos = [
    ("paginas/bandeja.py", "1 · La bandeja de un concesionario",
     "La lista de su concesionario, ya ordenada por riesgo, con el motivo principal de cada caso."),
    ("paginas/caso.py", "2 · Un caso, contado",
     "Una Ranger real: quién es, qué dicen sus datos y por qué está arriba de la lista."),
    ("paginas/resultados.py", "3 · ¿Funciona?",
     "Los resultados del modelo en meses que nunca vio, y por qué el número es honesto."),
]
for pagina, titulo, desc in pasos:
    a, b = st.columns([3, 1])
    a.markdown(f'<div class="paso"><b>{titulo}</b><br>{desc}</div>', unsafe_allow_html=True)
    b.page_link(pagina, label="Ir", icon="➡️")

with st.expander("Qué más hay en esta aplicación"):
    st.markdown(
        "- **Dashboard completo**: el tablero del equipo, con sus cinco pestañas y todos los filtros.\n"
        "- **Evidencia y tablas**: los análisis exploratorios, la revisión cruzada y las tablas generadas.\n"
        "- **Documentos**: el informe final y la presentación.\n"
        "- **Corridas**: recalcular el pipeline y los análisis en segundo plano, sin tocar la entrega oficial, "
        "y comparar el resultado nuevo con el entregado.")
