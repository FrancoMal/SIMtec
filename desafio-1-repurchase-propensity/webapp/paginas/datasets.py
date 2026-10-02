"""Carga de CSV y estado del conjunto activo para el flujo de trabajo."""
import json
from datetime import date

import pandas as pd
import streamlit as st

from lib import datasets as D
from lib.diseno import encabezado


def estado_archivo(path):
    if not path.is_file():
        return "Falta cargar", False
    if path.stat().st_size < 1024 and path.read_bytes().startswith(b"version https://git-lfs"):
        return "Pendiente de descargar", False
    return f"{path.stat().st_size / 1e6:,.1f} MB", True


encabezado("Carga de datos", "Elegí un conjunto guardado o cargá los dos archivos para comenzar un análisis.")
d = D.activo()
if aviso := st.session_state.pop("_dataset_guardado_aviso", None):
    st.success(f"{aviso} se guardó y quedó seleccionado. Ya podés continuar al entrenamiento.")

with st.container(border=True):
    detalle, siguiente = st.columns([3, 1], vertical_alignment="center")
    with detalle:
        st.subheader(d["nombre"])
        st.caption(f"Conjunto activo · datos hasta el {date.fromisoformat(d['cutoff']).strftime('%d/%m/%Y')}")
        registros, listos = [], []
        for tipo, etiqueta, archivo in (("ventas", "Ventas", D.VENTAS), ("agenda", "Agenda de servicios", D.AGENDA)):
            estado, listo = estado_archivo(d["raw"] / archivo)
            listos.append(listo)
            meta = d.get("archivos", {}).get(tipo, {})
            filas = f"{meta['filas']:,}".replace(",", ".") + " filas" if "filas" in meta else estado
            registros.append({"Archivo": etiqueta, "Estado": "Disponible" if listo else estado, "Contenido": filas,
                              "Nombre original": meta.get("archivo", archivo),
                              "Desde": meta.get("desde", "—"), "Hasta": meta.get("hasta", "—")})
        st.write("Ventas y agenda disponibles." if all(listos) else "Completá los archivos antes de entrenar.")
    with siguiente:
        st.page_link("paginas/corridas.py", label="Continuar al entrenamiento", disabled=not all(listos), width="stretch")
    with st.expander("Revisar archivos del conjunto activo"):
        st.dataframe(pd.DataFrame(registros), hide_index=True, width="stretch")
        for tipo, info in d.get("archivos", {}).items():
            for columna, cantidad in info.get("identificadores_vacios", {}).items():
                if cantidad:
                    st.warning(f"{tipo.capitalize()}: {cantidad:,} filas sin {columna}. Pueden quedar fuera del análisis.")
        if not all(listos):
            st.info("Cargá un nuevo conjunto debajo. Si elegiste el conjunto original, verificá que sus dos CSV estén descargados.")

st.subheader("Cargar un conjunto")
st.caption("Cada conjunto guarda sus propios archivos, entrenamiento y resultados.")
try:
    parametros = json.loads(d["params"].read_text(encoding="utf8"))["split"]
except (OSError, KeyError, json.JSONDecodeError):
    parametros = {"train_end": "2025-09-30", "valid_end": "2025-12-31"}

with st.form("nuevo_dataset", border=False):
    nombre = st.text_input("Nombre del conjunto", placeholder="Por ejemplo: Octubre 2026", max_chars=100)
    izquierda, derecha = st.columns(2)
    ventas = izquierda.file_uploader("Ventas", type=["csv"], key="csv_ventas", help="CSV con los datos de venta de los vehículos.")
    agenda = derecha.file_uploader("Agenda de servicios", type=["csv"], key="csv_agenda", help="CSV con turnos, servicios e historial de atención.")
    st.caption("CSV UTF-8 separados por comas. Los archivos pueden tener cualquier nombre. Máximo: 1 GB por archivo.")
    with st.expander("Fechas del análisis", expanded=False):
        st.write("Revisá estas fechas antes de guardar. Deben corresponder al período cubierto por los archivos.")
        st.caption("El modelo aprende con el primer período, se calibra con el segundo y se evalúa con los casos posteriores "
                   "que ya cerraron. El corte debe indicar hasta cuándo los eventos están completos.")
        a, b, c = st.columns(3)
        limites = {"min_value": date(1900, 1, 1), "max_value": date(2100, 12, 31)}
        train = a.date_input("Fin de entrenamiento", value=date.fromisoformat(parametros["train_end"]), **limites)
        valid = b.date_input("Fin de calibración", value=date.fromisoformat(parametros["valid_end"]), **limites)
        cutoff = c.date_input("Corte de datos", value=date.fromisoformat(d["cutoff"]), **limites)
    st.caption(f"Fechas iniciales: entrenamiento {train:%d/%m/%Y} · calibración {valid:%d/%m/%Y} · corte {cutoff:%d/%m/%Y}.")
    enviado = st.form_submit_button("Validar y usar este conjunto", type="primary")
if enviado:
    try:
        with st.spinner("Validando los CSV y guardando el conjunto…"):
            meta = D.guardar(nombre, ventas, agenda, cutoff, train, valid)
        # El shell aplica la selección antes de crear su selector global en el siguiente render.
        st.session_state["_dataset_pendiente"] = meta["id"]
        st.rerun()
    except Exception as e:
        st.error(f"No se pudo guardar el conjunto: {e}")

with st.expander("Formato de los archivos"):
    st.write("Conservá los nombres de columnas de los archivos originales. Las columnas adicionales se aceptan.")
    for titulo, archivo in (("Ventas", D.VENTAS), ("Agenda de servicios", D.AGENDA)):
        st.markdown(f"**{titulo}**")
        try:
            columnas = D._cabecera(D.original()["raw"] / archivo)
        except (OSError, UnicodeDecodeError):
            st.warning("No se pudo leer la referencia de columnas. Revisá que los CSV originales estén disponibles.")
        else:
            st.code(", ".join(c for c in columnas if c not in {"SalesType", "ScheduleModalityCode", "CancellationReason", "Quicklane"}), language=None)

with st.expander("Conjuntos guardados"):
    st.caption("Usá el selector de conjunto en la parte superior para cambiar de datos en toda la aplicación.")
    st.dataframe(pd.DataFrame([
        {"Conjunto": x["nombre"], "Corte de datos": x["cutoff"],
         "Estado": "Contactos calculados" if (x["resultados"] / "data/processed/contactos_por_cliente.parquet").exists()
         else "Modelo entrenado" if (x["resultados"] / "data/processed/scores_actuales.parquet").exists()
         else "Pendiente de entrenamiento"}
        for x in D.catalogo()
    ]), hide_index=True, width="stretch")
