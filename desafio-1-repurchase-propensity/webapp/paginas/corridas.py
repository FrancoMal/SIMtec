"""Entrenamiento y priorización con ejecución en segundo plano e historial."""
import json
import platform
import sys
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from lib import corridas as C
from lib.datasets import activo as dataset_activo, VENTAS, AGENDA
from lib.diseno import encabezado
from lib.fuentes import REPO


NOMBRES = {
    "pipeline": "Entrenamiento y contactos", "contacto": "Actualizar prioridad de contacto",
    "ablaciones": "Auditoría de leakage y robustez", "sensibilidad": "Sensibilidad de las ventanas",
    "eda": "Análisis exploratorio", "notebooks": "Notebooks de evidencia", "diccionario": "Diccionario de datos",
    "todo": "Análisis completo",
}


def duracion(segundos):
    segundos = max(0, int(segundos))
    minutos, segundos = divmod(segundos, 60)
    return f"{minutos} min {segundos:02d} s" if minutos else f"{segundos} s"


def nombre_corrida(e):
    return NOMBRES.get(e.get("clave"), e.get("titulo", "Ejecución"))


def estado_corrida(e):
    if e.get("fin") is None:
        return "En curso"
    return {0: "Completada", "cancelada": "Cancelada", "interrumpida": "Interrumpida"}.get(e.get("codigo"), "Falló")


def ejecutar(clave):
    try:
        with st.spinner("Iniciando la ejecución…"):
            C.lanzar(clave)
        st.session_state["_habia_activa"] = True
        st.rerun()
    except (RuntimeError, OSError) as exc:
        st.error(f"No se pudo iniciar: {exc}")


def paso_actual(e, log):
    if e.get("clave") == "contacto":
        return "Aplicando reglas de contacto y consolidando clientes", []
    if e.get("clave") != "pipeline":
        return nombre_corrida(e), []
    etapas = [
        ("parámetros de ventana:", "Preparar datos y ventanas"),
        ("features (evaluables)", "Construir variables del modelo"),
        ("entrenamiento + evaluación temporal", "Entrenar y evaluar el modelo"),
        ("SHAP…", "Calcular las explicaciones SHAP"),
        ("scoring población actual", "Calcular el riesgo de cada vehículo"),
        ("segunda etapa:", "Priorizar los contactos por cliente"),
        ("listo. resumen en", "Finalizar y guardar los resultados"),
    ]
    actual = max((i for i, (marca, _) in enumerate(etapas) if marca in log), default=-1)
    return (etapas[actual][1], [etiqueta for _, etiqueta in etapas[:actual]]) if actual >= 0 else ("Iniciando el proceso", [])


encabezado("Entrenamiento", "Generá el modelo y la lista priorizada de clientes con el conjunto activo.")
d = dataset_activo()
activa = C.activa()
hay_pipeline = C.pipeline_corrido()
historial = C.historial()
archivos_listos, faltantes = True, []
for etiqueta, archivo in (("ventas", VENTAS), ("agenda de servicios", AGENDA)):
    path = d["raw"] / archivo
    if not path.is_file() or (path.stat().st_size < 1024 and path.read_bytes().startswith(b"version https://git-lfs")):
        archivos_listos = False
        faltantes.append(etiqueta)

if not archivos_listos:
    st.warning("Faltan archivos disponibles de " + " y ".join(faltantes) + ". Cargá los datos antes de entrenar.")
    st.page_link("paginas/datasets.py", label="Ir a carga de datos")
elif not hay_pipeline:
    st.info("Este conjunto está listo para su primer entrenamiento.")

try:
    split = json.loads(d["params"].read_text(encoding="utf8"))["split"]
except (OSError, KeyError, json.JSONDecodeError):
    split = {}
with st.container(border=True):
    st.markdown(f"**{d['nombre']}**")
    st.caption(f"Corte de datos: {d['cutoff']} · entrenamiento hasta {split.get('train_end', 'sin definir')} "
               f"· calibración hasta {split.get('valid_end', 'sin definir')}")
    contenido, accion = st.columns([3, 1.3], vertical_alignment="center")
    with contenido:
        st.subheader("Entrenar y priorizar")
        st.write("Procesa los CSV, entrena y evalúa el modelo, calcula SHAP y aplica el segundo filtro de contactos.")
        previas = [e for e in historial if e.get("clave") == "pipeline" and e.get("codigo") == 0 and e.get("fin")]
        if previas:
            st.caption("Última ejecución completada: " + duracion(previas[0]["fin"] - previas[0]["inicio"]) + ". El tiempo puede variar según el volumen de datos.")
        else:
            st.caption("La duración quedará registrada al terminar. Podés seguir navegando mientras se ejecuta.")
    with accion:
        if st.button("Entrenar y priorizar", key="run_pipeline", type="primary", width="stretch",
                     disabled=activa is not None or not archivos_listos):
            ejecutar("pipeline")
    if hay_pipeline:
        st.caption("Una nueva ejecución actualizará el modelo y los resultados de este conjunto.")

if hay_pipeline:
    descripcion, accion = st.columns([3, 1.3], vertical_alignment="center")
    with descripcion:
        st.markdown("**Actualizar solo los contactos**")
        st.caption("Reaplica el segundo filtro con el scoring y SHAP existentes. Conserva el modelo entrenado.")
    with accion:
        if st.button("Actualizar contactos", key="run_contacto", disabled=activa is not None, width="stretch"):
            ejecutar("contacto")


@st.fragment(run_every=2)
def en_curso():
    e = C.activa()
    if not e:
        if st.session_state.get("_habia_activa"):
            st.session_state["_habia_activa"] = False
            st.cache_data.clear()
            st.rerun(scope="app")
        return
    st.session_state["_habia_activa"] = True
    registro = C.log(e, 400)
    etapa, completadas = paso_actual(e, registro)
    st.divider()
    if e.get("dataset_id", "original") != d["id"]:
        st.info(f"Hay una ejecución de otro conjunto: {e.get('dataset_nombre', 'Dataset original')}. Solo puede ejecutarse un proceso a la vez.")
    with st.status(nombre_corrida(e) + " en curso", state="running", expanded=True):
        info, control = st.columns([3, 1], vertical_alignment="center")
        info.markdown(f"**{etapa}**")
        info.caption(f"{e.get('dataset_nombre', 'Dataset original')} · {duracion(time.time() - e['inicio'])} transcurridos")
        if control.button("Cancelar ejecución", key="cancelar_corrida", width="stretch"):
            C.cancelar(e)
            st.rerun(scope="app")
        if completadas:
            st.caption("Completado: " + "; ".join(completadas) + ".")
    with st.expander("Ver registro en vivo"):
        st.code(registro or "Iniciando el proceso…", language=None)


en_curso()

if activa is None:
    ultima = next((e for e in historial if e.get("clave") in {"pipeline", "contacto"} and e.get("fin")), None)
    if ultima:
        estado = estado_corrida(ultima)
        cuando = datetime.fromtimestamp(ultima["fin"]).strftime("%d/%m/%Y %H:%M")
        resumen = f"{nombre_corrida(ultima)} · {cuando} · {duracion(ultima['fin'] - ultima['inicio'])}."
        if estado == "Completada":
            st.success("Resultados actualizados. " + resumen)
        elif estado == "Falló":
            st.error("La última ejecución falló. Revisá el registro en el historial y corregí el problema antes de volver a ejecutar.")
            st.caption(resumen)
        else:
            st.warning(f"La última ejecución quedó {estado.lower()}. Podés iniciarla de nuevo.")
            st.caption(resumen)
    if (d["resultados"] / "data/processed/contacto_resumen.json").exists():
        st.page_link("paginas/contactos.py", label="Ver resultados y contactos")
        st.page_link("paginas/eficiencia.py", label="Revisar eficiencia del modelo")

with st.expander("Historial de ejecuciones", expanded=False):
    st.caption("Ejecuciones realizadas desde la aplicación para el conjunto activo.")
    if not historial:
        st.write("Todavía no hay ejecuciones registradas para este conjunto.")
    else:
        filas = [{"Inicio": datetime.fromtimestamp(e["inicio"]).strftime("%d/%m/%Y %H:%M"),
                  "Proceso": nombre_corrida(e), "Estado": estado_corrida(e),
                  "Duración": duracion((e.get("fin") or time.time()) - e["inicio"])} for e in historial]
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
        elegida = st.selectbox("Registro de ejecución", range(len(historial)), key="historial_corrida",
                              format_func=lambda i: f"{filas[i]['Inicio']} · {filas[i]['Proceso']} · {filas[i]['Estado']}")
        registro = C.log(historial[elegida], 1000)
        st.code(registro or "Sin registro disponible.", language=None)
        st.download_button("Descargar registro", registro, file_name="registro_ejecucion.txt", mime="text/plain")

if d["id"] == "original":
    with st.expander("Análisis complementarios", expanded=False):
        st.caption("Revisiones del estudio original. La auditoría de leakage y robustez alimenta el dashboard de eficiencia.")
        opciones = ["ablaciones", "sensibilidad", "eda", "notebooks", "diccionario"]
        elegida = st.selectbox("Análisis", opciones, format_func=NOMBRES.get, key="analisis_complementario")
        descripciones = {
            "ablaciones": "Compara variantes del modelo en el mismo test para revisar leakage y robustez.",
            "sensibilidad": "Compara cómo cambian las ventanas al ajustar las reglas temporales.",
            "eda": "Genera tablas y gráficos para explorar los datos del estudio.",
            "notebooks": "Genera los notebooks de evidencia de datos, ventanas y modelo.",
            "diccionario": "Actualiza la descripción de las columnas del conjunto analítico.",
        }
        st.write(descripciones[elegida])
        if st.button("Ejecutar análisis", key="run_complementario", disabled=activa is not None or not hay_pipeline):
            ejecutar(elegida)

with st.expander("Diagnóstico técnico", expanded=False):
    st.dataframe(pd.DataFrame([
        {"Dato": "Python", "Valor": f"{platform.python_version()} ({sys.executable})"},
        {"Dato": "Proyecto", "Valor": str(REPO)}, {"Dato": "Archivos de entrada", "Valor": str(d["raw"])},
        {"Dato": "Carpeta de resultados", "Valor": str(d["resultados"])},
        {"Dato": "Configuración temporal", "Valor": str(d["params"])},
    ]), hide_index=True, width="stretch")
