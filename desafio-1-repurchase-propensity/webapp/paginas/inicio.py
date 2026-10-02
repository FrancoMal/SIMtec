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
    f"En la evaluación de este conjunto, **{pct(k['base'])} de las ventanas de mantenimiento no terminan en un "
    f"service en un concesionario oficial**. Esta solución ordena la lista para priorizar el contacto, "
    f"y explica por qué. Hoy la lista tiene **{miles(len(s))} vehículos**.")

c1, c2, c3 = st.columns(3)
c1.markdown(f"""<div class="tarjeta"><div class="etiqueta">Etapa 1 · precisión en test</div>
<div class="numero">{round(k['prec20'] * 10)} de 10</div>
ventanas del 20 % de mayor riesgo terminaron en abandono. La proporción general fue {round(k['base'] * 10)} de 10.</div>""",
            unsafe_allow_html=True)
c2.markdown(f"""<div class="tarjeta"><div class="etiqueta">Etapa 1 · cobertura en test</div>
<div class="numero">{pct(k['recall_mes'])}</div>
de los abandonos quedan incluidos al simular una capacidad de {miles(k['contactos_mes'])} casos por mes.</div>""",
            unsafe_allow_html=True)
c3.markdown(f"""<div class="tarjeta"><div class="etiqueta">Probado en meses que no vio</div>
<div class="numero">{miles(k['n_test'])}</div>
ventanas de {k['test_desde']} a {k['test_hasta']}, con un modelo entrenado hasta {k['train_end']}.</div>""",
            unsafe_allow_html=True)

st.subheader("Del análisis a la lista de contacto")
st.markdown("**CSV → riesgo y SHAP → grupos 20 / 30 / 50 → Alto + Medio → filtro operativo por cliente → lista final.**")
st.caption("La segunda etapa aplica reglas de oportunidad y evita contactos duplicados. Las métricas anteriores "
           "evalúan el modelo de riesgo; el efecto del contacto todavía debe medirse.")
st.page_link("paginas/contactos.py", label="Ver la lista final de contactos priorizados")
st.subheader("Recorrido de la demo")
st.caption("Todo se lee de los resultados ya generados.")
pasos = [
    ("paginas/bandeja.py", "1 · La bandeja de un concesionario",
     "Los clientes seleccionados por la segunda etapa, con su riesgo, tres motivos SHAP y motivos operativos."),
    ("paginas/caso.py", "2 · Un caso, contado",
     "Una Ranger real: quién es, qué dicen sus datos y por qué está arriba de la lista."),
    ("paginas/resultados.py", "3 · ¿Funciona?",
     "Los resultados del modelo en meses que nunca vio, y por qué el número es honesto."),
]
for pagina, titulo, desc in pasos:
    a, b = st.columns([3, 1])
    a.markdown(f'<div class="paso"><b>{titulo}</b><br>{desc}</div>', unsafe_allow_html=True)
    b.page_link(pagina, label="Ir")

with st.expander("Qué más hay en esta aplicación"):
    st.markdown(
        "- **Dashboard completo**: el tablero del equipo, con sus cinco pestañas y todos los filtros.\n"
        "- **Evidencia y tablas**: los análisis exploratorios, la revisión cruzada y las tablas generadas.\n"
        "- **Documentos**: el informe final y la presentación.\n"
        "- **Corridas**: recalcular el pipeline y los análisis en segundo plano, sin tocar la entrega oficial, "
        "y comparar el resultado nuevo con el entregado.")
