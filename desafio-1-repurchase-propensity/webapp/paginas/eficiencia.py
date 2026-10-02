"""Calidad, tiempos y trazabilidad del modelo del dataset activo."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import corridas as C
from lib.diseno import BLUE, MUTED, encabezado, estilo_grafico
from lib.eficiencia import (cruces_horizonte, duracion, fila_modelo, soporte_temporal,
                            tabla_shap, telemetria_del_modelo)
from lib.fuentes import csv, miles, mtime, pct, rutas, texto


encabezado("Eficiencia del modelo", "Evaluá la calidad del ranking, el tiempo de procesamiento y las señales que explican el riesgo.")
r = rutas()


def leer_csv(path):
    return csv(path) if path.is_file() else pd.DataFrame()


def leer_json(path):
    return json.loads(texto(path)) if path.is_file() else {}


@st.cache_data(show_spinner=False)
def leer_parquet(path: str, actualizacion: float):
    return pd.read_parquet(path)


def grafico(fig, **kwargs):
    st.plotly_chart(estilo_grafico(fig), width="stretch", **kwargs)


def numero(valor, decimales=3):
    return f"{valor:.{decimales}f}".replace(".", ",") if pd.notna(valor) else "Sin registro"


def fecha_registro(timestamp):
    return datetime.fromtimestamp(timestamp, ZoneInfo("America/Buenos_Aires")).strftime("%d/%m/%Y %H:%M") + " (Argentina)"


AYUDAS_METRICAS = {
    "modelo": "Modelo o criterio de comparación evaluado sobre el test temporal.",
    "n": "Cantidad de ventanas evaluadas en el test. Un mismo vehículo puede tener varias ventanas; no es la cantidad de clientes únicos.",
    "base_rate": "Proporción de ventanas del test en las que se observó abandono. Va de 0 a 1 y sirve como referencia para interpretar la PR-AUC.",
    "roc_auc": "Capacidad de ordenar los casos con abandono por encima de los casos con retorno. Mayor es mejor: 0,5 equivale al azar y 1 a una separación perfecta.",
    "pr_auc": "Precisión media (AP), que resume la relación entre precisión y recall al identificar abandonos. Mayor es mejor; comparala con la tasa de abandono del test (base_rate).",
    "brier": "Promedio del error cuadrático entre la probabilidad estimada y el resultado observado (0 o 1). Menor es mejor; 0 indica probabilidades sin error.",
    "log_loss": "Error de las probabilidades que penaliza especialmente las predicciones incorrectas hechas con mucha confianza. Menor es mejor; 0 indica predicciones perfectas.",
    "ece": "Error de calibración esperado: diferencia media ponderada entre las probabilidades estimadas y las tasas de abandono observadas, agrupadas por rango. Menor es mejor; 0 indica coincidencia en esos grupos.",
}
AYUDA_SHAP_GLOBAL = "Promedio del valor absoluto de SHAP en la muestra de test. Mide cuánto influye una variable, sin indicar si aumenta o reduce el riesgo. Está en log-odds del modelo antes de calibrar; no son puntos de probabilidad."
AYUDA_SHAP_LOCAL = "Aporte de este motivo al score del modelo antes de calibrar, en log-odds. Un valor positivo aumenta el riesgo de abandono y uno negativo lo reduce. Los tres motivos no suman la probabilidad ni miden el efecto de contactar al cliente."


info = leer_json(r["models"] / "info.json")
metricas = leer_csv(r["models"] / "metricas_test.csv")
principal = fila_modelo(metricas)
tiempos = leer_json(r["modelo"] / "tiempos_pipeline.json")
if tiempos and tiempos.get("estado") != "completo":
    st.warning("La última ejecución no finalizó un entrenamiento completo. Sus archivos pueden corresponder a distintas etapas; completá el entrenamiento para consultar métricas consistentes.")
    a, b = st.columns(2)
    a.metric("Estado de la última ejecución", {"error": "Fallida", "ejecutando": "Iniciada",
               "solo_features": "Sólo variables"}.get(tiempos.get("estado"), "Incompleta"))
    b.metric("Tiempo registrado", duracion(tiempos.get("segundos_total")))
    etapas = pd.DataFrame(tiempos.get("etapas", []))
    if not etapas.empty:
        st.dataframe(etapas, hide_index=True, width="stretch")
    if tiempos.get("error"):
        with st.expander("Detalle del error"):
            st.code(tiempos["error"], language=None)
    st.page_link("paginas/corridas.py", label="Ir a entrenamiento")
    st.stop()
if not info or not principal:
    st.info("Todavía no hay un modelo evaluado para este dataset. Ejecutá el entrenamiento para ver sus métricas y explicaciones.")
    st.page_link("paginas/corridas.py", label="Ir a entrenamiento")
    if tiempos and tiempos.get("estado") == "error":
        st.warning("El último entrenamiento falló. Revisá el registro de la ejecución antes de volver a intentarlo.")
    st.stop()

st.caption("Evaluación del modelo de riesgo sobre el test temporal. El filtro de contacto usa reglas operativas; su efecto sobre el retorno todavía no está medido.")
st.caption(f"Modelo guardado: {fecha_registro(mtime(r['models'] / 'info.json'))}.")
for col, campo, etiqueta in zip(st.columns(4), ["roc_auc", "pr_auc", "brier", "ece"],
        ["ROC-AUC", "PR-AUC", "Error Brier", "Error de calibración"]):
    col.metric(etiqueta, numero(principal.get(campo)), help=AYUDAS_METRICAS[campo])

calidad, rendimiento, controles, shap = st.tabs(["Calidad", "Tiempos", "Controles de datos", "SHAP"])

with calidad:
    st.subheader("Capacidad y precisión")
    capacidades = leer_csv(r["models"] / "capacidad_LightGBM_calibrado.csv")
    if not capacidades.empty:
        opciones = capacidades.capacidad_pct.tolist()
        elegido = st.select_slider("Porción del test que se prioriza", options=opciones,
                                    value=min(opciones, key=lambda v: abs(v - .2)),
                                    format_func=lambda v: pct(v), key="eficiencia_capacidad")
        capacidad = capacidades.loc[capacidades.capacidad_pct.eq(elegido)].iloc[0]
        a, b, c, d = st.columns(4)
        a.metric("Ventanas priorizadas", miles(capacidad.contactados), help="Cantidad de ventanas del test dentro de la porción seleccionada del ranking. No equivale a clientes únicos.")
        b.metric("Precisión", pct(capacidad.precision, 1), help="Abandonos observados entre las ventanas priorizadas.")
        c.metric("Abandonos incluidos", pct(capacidad.recall, 1), help="Recall: proporción de todos los abandonos del test incluida en el ranking seleccionado.")
        d.metric("Lift sobre el promedio", f"{numero(capacidad.lift, 2)}×", help="Precisión de la selección dividida por la tasa de abandono del test. Un lift de 2 significa el doble de abandonos por ventana priorizada que una selección al azar.")
        st.caption("Esta simulación usa ventanas del test; no es el cupo de clientes del segundo filtro.")
    izq, der = st.columns(2, gap="large")
    with izq:
        st.markdown("**Cobertura según capacidad**")
        if capacidades.empty:
            st.info("No se guardó la curva de capacidad para este entrenamiento.")
        else:
            fig = go.Figure(go.Scatter(x=capacidades.capacidad_pct, y=capacidades.recall,
                        mode="lines+markers", name="Modelo", line=dict(color=BLUE, width=3),
                        hovertemplate="Capacidad %{x:.0%}<br>Abandonos incluidos %{y:.1%}<extra></extra>"))
            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name="Selección al azar",
                                    line=dict(color=MUTED, dash="dot")))
            fig.update_layout(height=340, xaxis=dict(title="Porción priorizada", tickformat=".0%"),
                              yaxis=dict(title="Abandonos incluidos", tickformat=".0%", range=[0, 1]))
            grafico(fig)
    with der:
        st.markdown("**Probabilidad estimada y abandono observado**")
        calibracion = leer_csv(r["models"] / "calibracion_LightGBM_calibrado.csv")
        if calibracion.empty:
            st.info("No se guardó la curva de calibración para este entrenamiento.")
        else:
            fig = go.Figure(go.Scatter(x=calibracion.score_medio, y=calibracion.tasa_observada,
                        mode="lines+markers", name="Modelo", line=dict(color=BLUE, width=3),
                        customdata=calibracion[["n"]],
                        hovertemplate="Estimado %{x:.1%}<br>Observado %{y:.1%}<br>%{customdata[0]} ventanas<extra></extra>"))
            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name="Calibración ideal",
                                    line=dict(color=MUTED, dash="dot")))
            fig.update_layout(height=340, xaxis=dict(title="Probabilidad media", tickformat=".0%", range=[0, 1]),
                              yaxis=dict(title="Tasa observada", tickformat=".0%", range=[0, 1]))
            grafico(fig)
    st.subheader("Períodos de entrenamiento y evaluación")
    st.dataframe(soporte_temporal(info), hide_index=True, width="stretch",
                 column_config={"Tasa de abandono": st.column_config.NumberColumn(format="percent"),
                                "Ventanas": st.column_config.NumberColumn(format="localized")})
    with st.expander("Comparar modelos y descargar métricas"):
        st.dataframe(metricas, hide_index=True, width="stretch",
                     column_config={
                         "modelo": st.column_config.TextColumn(help=AYUDAS_METRICAS["modelo"]),
                         "n": st.column_config.NumberColumn(help=AYUDAS_METRICAS["n"]),
                         "base_rate": st.column_config.NumberColumn(help=AYUDAS_METRICAS["base_rate"]),
                         **{c: st.column_config.NumberColumn(format="%.4f", help=AYUDAS_METRICAS[c])
                            for c in ["roc_auc", "pr_auc", "brier", "log_loss", "ece"]},
                     })
        st.download_button("Descargar métricas", metricas.to_csv(index=False).encode("utf-8-sig"),
                           "metricas_modelo.csv", "text/csv", key="descarga_metricas")

with rendimiento:
    st.subheader("Tiempo de procesamiento")
    vigente = telemetria_del_modelo(tiempos, mtime(r["models"] / "info.json"))
    if tiempos:
        estado = tiempos.get("estado", "sin registro")
        if vigente:
            st.caption("Mediciones de la ejecución que generó el modelo mostrado.")
        elif estado == "ejecutando":
            st.info("Hay una medición parcial de una ejecución iniciada. Consultá Entrenamiento para ver si sigue activa.")
        elif estado == "error":
            st.warning("La última ejecución falló. Estos tiempos son parciales y no certifican que las salidas formen un resultado completo.")
        else:
            st.info("Esta medición no corresponde a un entrenamiento completo del modelo mostrado. Se presenta sólo como registro de ejecución.")
        a, b, c = st.columns(3)
        a.metric("Tiempo registrado", duracion(tiempos.get("segundos_total")))
        b.metric("Estado", {"completo": "Completado", "error": "Fallido", "ejecutando": "En proceso",
                            "solo_features": "Sólo variables"}.get(estado, estado))
        c.metric("Variables del modelo", miles(info["n_features"]) if info.get("n_features") else "Sin registro")
        etapas = pd.DataFrame(tiempos.get("etapas", []))
        if not etapas.empty and {"nombre", "segundos", "estado"}.issubset(etapas):
            medidas = etapas.dropna(subset=["segundos"])
            if not medidas.empty:
                fig = go.Figure(go.Bar(y=medidas.nombre, x=medidas.segundos, orientation="h",
                                marker_color=BLUE, hovertemplate="%{y}<br>%{x:.2f} segundos<extra></extra>"))
                fig.update_layout(height=max(340, len(medidas) * 34), showlegend=False,
                                  xaxis_title="Segundos medidos", yaxis=dict(autorange="reversed"))
                grafico(fig)
            with st.expander("Registro de tiempos"):
                st.dataframe(etapas[["nombre", "segundos", "estado"]].rename(
                    columns={"nombre": "Etapa", "segundos": "Segundos", "estado": "Estado"}),
                    hide_index=True, width="stretch")
                inicio = tiempos.get("inicio")
                inicio_visible = fecha_registro(datetime.fromisoformat(inicio).timestamp()) if inicio else "Sin registro"
                st.caption(f"Inicio: {inicio_visible} · Corte: {tiempos.get('cutoff', 'Sin registro')}")
                st.download_button("Descargar registro", json.dumps(tiempos, ensure_ascii=False, indent=2),
                                   "tiempos_pipeline.json", "application/json")
        st.caption("Tiempo de pared del proceso: incluye lectura, cálculo y exportación. Entrenamiento incluye los modelos de comparación y la calibración. SHAP actual está incluido en scoring.")
    else:
        st.info("Este modelo se generó antes del registro por etapas. El próximo entrenamiento guardará los tiempos automáticamente.")
        corridas = [e for e in C.historial() if e.get("clave") in ("pipeline", "todo")
                    and e.get("codigo") == 0 and e.get("inicio") and e.get("fin")]
        if corridas:
            ultima = max(corridas, key=lambda e: e["fin"])
            st.metric("Última ejecución completa registrada", duracion(ultima["fin"] - ultima["inicio"]))
            st.caption(f"Registro del {fecha_registro(ultima['inicio'])}. "
                       "Tiempo total del trabajo; puede incluir otras tareas y no permite reconstruir los tiempos de cada etapa.")
        st.page_link("paginas/corridas.py", label="Ir a entrenamiento")

with controles:
    st.subheader("Controles de fuga de información")
    st.write("La fuga de información ocurre cuando el modelo usa datos que todavía no estaban disponibles al decidir. Estos controles muestran la configuración y la evidencia disponible para este dataset.")
    snapshot = info.get("exclude_snapshot")
    if snapshot is True:
        st.success("La corrida excluyó el estado de conectividad tomado al extraer los datos (ConnectedStatusARG).")
    elif snapshot is False:
        st.warning("La corrida incluyó el estado de conectividad tomado al extraer los datos. Revisá su disponibilidad histórica antes de usar el modelo.")
    else:
        st.info("Esta corrida no registró si excluyó el estado de conectividad.")
    st.dataframe(pd.DataFrame([
        {"Control": "Separación temporal", "Evidencia": "Fechas y soporte registrados en la pestaña Calidad.", "Alcance": "Configuración de la corrida"},
        {"Control": "Eventos y encuestas previos", "Evidencia": "El cálculo usa eventos anteriores a la fecha de scoring.", "Alcance": "Regla implementada; no es una auditoría completa"},
        {"Control": "Kilometraje histórico", "Evidencia": "Las variables usan VehicleCurrentKM del evento; no la foto KM de extracción.", "Alcance": "Regla implementada"},
        {"Control": "Variables objetivo e identificadores", "Evidencia": "El selector excluye etiquetas, resultados futuros e identificadores como predictores.", "Alcance": "Regla implementada"},
    ]), hide_index=True, width="stretch")
    st.markdown("**Horizontes que cruzan los cortes temporales**")
    pventanas = r["processed"] / "ventanas.parquet"
    cruces = cruces_horizonte(leer_parquet(str(pventanas), mtime(pventanas)), info) if pventanas.is_file() else pd.DataFrame()
    if cruces.empty:
        st.info("No hay ventanas o fechas suficientes para revisar el cruce de horizontes en este dataset.")
    else:
        st.dataframe(cruces, hide_index=True, width="stretch",
                     column_config={"Proporción": st.column_config.NumberColumn(format="percent")})
        if cruces["Horizontes que cruzan"].sum():
            st.warning("Hay ventanas cuyo horizonte de resultado termina después del corte de su período. El entrenamiento actual separa por fecha de scoring; no aplica purga ni embargo por horizonte. Revisá este solapamiento antes de interpretar las métricas como una simulación estricta de disponibilidad histórica.")
        else:
            st.caption("No se observan cruces de horizonte en estos dos cortes. Este control no descarta otras fuentes de fuga.")
    ablaciones_path = r["modelo"] / "ablaciones.csv"
    ablaciones = leer_csv(ablaciones_path)
    with st.expander("Comparaciones de robustez y leakage"):
        if ablaciones.empty:
            st.info("No hay ablaciones guardadas para este dataset. Las métricas de otras bases no se usan como evidencia para éste.")
        else:
            st.caption(f"Análisis complementario guardado el {fecha_registro(mtime(ablaciones_path))}. Verificá que sus períodos y variantes correspondan al entrenamiento que querés comparar.")
            st.dataframe(ablaciones, hide_index=True, width="stretch")
            st.download_button("Descargar comparaciones", ablaciones.to_csv(index=False).encode("utf-8-sig"),
                               "ablaciones.csv", "text/csv")
    st.caption("Estos controles no certifican ausencia total de leakage. La evaluación está hecha por ventanas; no es una prueba de generalización a clientes nunca observados.")

with shap:
    st.subheader("Qué variables pesan en el riesgo")
    importancia = tabla_shap(leer_csv(r["models"] / "shap_global.csv"))
    if importancia.empty:
        st.info("No hay valores SHAP globales en su unidad original para este entrenamiento. Volvé a entrenar para generarlos.")
    else:
        col_opciones, col_texto = st.columns([1, 3])
        opciones = [v for v in (10, 20, 40) if v < len(importancia)] + [len(importancia)]
        top = col_opciones.selectbox("Variables a mostrar", opciones, key="shap_top")
        col_texto.caption("Magnitud media absoluta de SHAP en la muestra de test, en log-odds del LightGBM antes de calibrar. Una barra mayor indica más influencia en sus predicciones; no representa puntos de probabilidad ni efecto de contactar.")
        tabla = importancia.head(top)
        fig = go.Figure(go.Bar(y=tabla.Variable, x=tabla["SHAP absoluto medio"], orientation="h",
                              marker_color=BLUE, customdata=tabla[["Código"]],
                              hovertemplate="%{y}<br>SHAP medio %{x:.4f} log-odds<br>%{customdata[0]}<extra></extra>"))
        fig.update_layout(height=max(380, 28 * len(tabla)), yaxis=dict(autorange="reversed"),
                          xaxis_title="SHAP absoluto medio (log-odds)")
        grafico(fig)
        with st.expander("Ver y descargar el scoring SHAP"):
            st.dataframe(importancia, hide_index=True, width="stretch",
                         column_config={
                             "Variable": st.column_config.TextColumn(help="Nombre de la variable utilizada por el modelo para estimar el riesgo de abandono."),
                             "Código": st.column_config.TextColumn(help="Identificador de la variable en los datos del modelo."),
                             "SHAP absoluto medio": st.column_config.NumberColumn(format="%.4f", help=AYUDA_SHAP_GLOBAL),
                         })
            st.download_button("Descargar SHAP global", importancia.to_csv(index=False).encode("utf-8-sig"),
                               "shap_global.csv", "text/csv")
    muestra_path = r["models"] / "test_drivers_muestra.parquet"
    if muestra_path.is_file():
        muestra = leer_parquet(str(muestra_path), mtime(muestra_path))
        st.markdown("**Explicaciones individuales del test**")
        st.caption(f"Muestra de {miles(len(muestra))} ventanas. Cada valor SHAP positivo eleva el score bruto y cada valor negativo lo reduce; los tres motivos no suman la probabilidad calibrada.")
        buscar = st.text_input("Buscar vehicle_id o window_id", key="shap_busqueda")
        filtro = muestra
        if buscar.strip():
            filtro = muestra[muestra["vehicle_id"].astype(str).str.contains(buscar.strip(), regex=False, case=False)
                             | muestra["window_id"].astype(str).str.contains(buscar.strip(), regex=False, case=False)]
        columnas = ["vehicle_id", "window_id", "scoring_date", "label_churn", "p_lgbm_cal"]
        columnas += [f"driver_{i}{sufijo}" for i in range(1, 4) for sufijo in ("", "_shap")]
        nombres = {"scoring_date": "fecha", "label_churn": "abandono_observado", "p_lgbm_cal": "probabilidad"}
        nombres.update({f"driver_{i}": f"motivo_SHAP_{i}" for i in range(1, 4)})
        nombres.update({f"driver_{i}_shap": f"SHAP_{i}_log_odds" for i in range(1, 4)})
        visible = filtro[[c for c in columnas if c in filtro]].rename(columns=nombres)
        st.dataframe(visible, hide_index=True, width="stretch", height=360,
                     column_config={
                         "vehicle_id": st.column_config.TextColumn(help="Identificador del vehículo evaluado."),
                         "window_id": st.column_config.TextColumn(help="Identificador de la ventana de evaluación de ese vehículo."),
                         "fecha": st.column_config.Column(help="Fecha de scoring: momento en que se estimó el riesgo usando la información disponible hasta esa fecha."),
                         "abandono_observado": st.column_config.NumberColumn(help="Resultado real de la ventana: 1 indica abandono y 0 indica retorno dentro del horizonte evaluado."),
                         "probabilidad": st.column_config.NumberColumn(format="%.4f", help="Probabilidad calibrada de abandono, de 0 a 1. No es la probabilidad de volver si se contacta al cliente."),
                         **{f"motivo_SHAP_{i}": st.column_config.TextColumn(help=f"Motivo {i} entre los tres aportes SHAP de mayor magnitud para esta ventana.") for i in range(1, 4)},
                         **{f"SHAP_{i}_log_odds": st.column_config.NumberColumn(format="%+.4f", help=AYUDA_SHAP_LOCAL) for i in range(1, 4)},
                     })
        st.download_button("Descargar muestra filtrada", visible.to_csv(index=False).encode("utf-8-sig"),
                           "shap_test_filtrado.csv", "text/csv")
