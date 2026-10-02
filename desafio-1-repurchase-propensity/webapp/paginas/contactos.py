"""Espacio de trabajo para actuar sobre la segunda etapa y consultar su trazabilidad."""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.datasets import activo
from lib.diseno import encabezado, estilo_grafico
from lib.fuentes import contactos, miles, pct, requiere_contactos, resumen_contacto, scores, texto
from lib.listado import tabla_completa
from lib.resultados import (ESTADOS_CLIENTE, concesionarios, csv_resultados,
                            filtrar_resultados, preparar_contactos)


encabezado("Resultados", "Organizá el contacto con los clientes priorizados y consultá el motivo de cada decisión.")
requiere_contactos()
resumen = resumen_contacto()
clientes = preparar_contactos(contactos())
candidatos = preparar_contactos(contactos(candidatos=True))
dataset_id = activo()["id"]
prefijo = f"resultados_{dataset_id}"


def configuracion_columnas():
    configuracion = {
        "orden_contacto": st.column_config.NumberColumn("Prioridad", format="%d", width="small"),
        "customer_id": st.column_config.TextColumn("customer_id"),
        "vehicle_id": st.column_config.TextColumn("vehicle_id"),
        "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        "probabilidad": st.column_config.NumberColumn("Probabilidad de abandono", format="%.4f", min_value=0, max_value=1),
        "grupo": st.column_config.TextColumn("Grupo inicial", width="small"),
        "situacion": st.column_config.TextColumn("Situación"),
        "concesionario": st.column_config.TextColumn("Concesionario"),
        "motivos_operativos": st.column_config.TextColumn("Motivos de la prioridad", width="large"),
        "vehiculos_cliente": st.column_config.TextColumn("Vehículos asociados en Alto + Medio", width="large"),
        "dias_restantes": st.column_config.NumberColumn("Días de margen", format="%d"),
    }
    for i in (1, 2, 3):
        configuracion[f"motivo_SHAP_{i}"] = st.column_config.TextColumn(f"Motivo SHAP {i}", width="large")
    return configuracion


def filtros(tabla, clave, *, auditoria=False, inicial=False):
    columnas = st.columns([1, 1.45, 2.1] if inicial else [1, 1, 1.45, 2.1])
    situacion = "Todos"
    if not inicial:
        opciones = ["Todos"] + list(dict.fromkeys(
            ESTADOS_CLIENTE + (list(tabla["situacion"].dropna().unique()) if auditoria else [])))
        clave_situacion = f"{clave}_situacion"
        por_defecto = None if clave_situacion in st.session_state else (0 if auditoria else 1)
        situacion = columnas[0].selectbox("Situación", opciones, index=por_defecto,
                                         key=clave_situacion)
    inicio = 0 if inicial else 1
    grupo = columnas[inicio].selectbox("Grupo inicial", ["Todos", "Alto", "Medio"] + (["Bajo"] if inicial else []),
                                 key=f"{clave}_grupo")
    dealer = columnas[inicio + 1].selectbox("Concesionario", ["Todos"] + sorted(concesionarios(tabla).unique().tolist()),
                                  key=f"{clave}_dealer")
    busqueda = columnas[inicio + 2].text_input("Buscar cliente o vehículo", placeholder="Ingresá un identificador",
                                     key=f"{clave}_busqueda")

    def restablecer():
        st.session_state[f"{clave}_grupo"] = "Todos"
        st.session_state[f"{clave}_dealer"] = "Todos"
        st.session_state[f"{clave}_busqueda"] = ""
        if not inicial:
            st.session_state[f"{clave}_situacion"] = "Todos" if auditoria else "Seleccionado"

    st.button("Restablecer filtros", key=f"{clave}_restablecer", on_click=restablecer)
    return filtrar_resultados(tabla, situacion=situacion, grupo=grupo, concesionario=dealer, busqueda=busqueda)


def mostrar_tabla(tabla, clave, *, inicial=False):
    principal = (["orden_contacto", "situacion"] if not inicial else []) + [
        "customer_id", "vehicle_id", "fecha", "probabilidad", "grupo", "concesionario",
        "motivo_SHAP_1", "motivo_SHAP_2", "motivo_SHAP_3"]
    if not inicial:
        principal += ["motivos_operativos", "vehiculos_cliente", "dias_restantes"]
    st.dataframe(tabla, column_order=principal, column_config=configuracion_columnas(),
                 hide_index=True, width="stretch", height=420, key=f"{clave}_tabla")
    if tabla.empty:
        st.info("No hay coincidencias. Cambiá la situación, el grupo o el concesionario, o borrá la búsqueda.")
    st.download_button("Descargar vista filtrada", csv_resultados(tabla),
                       file_name=f"{clave}.csv", mime="text/csv", key=f"{clave}_descargar",
                       disabled=tabla.empty)


def valor(dato, decimales=0):
    return "Sin dato" if pd.isna(dato) else f"{float(dato):.{decimales}f}".replace(".", ",")


def detalle_cliente(tabla):
    if tabla.empty:
        return
    with st.expander("Consultar un cliente y sus motivos", expanded=False):
        # El identificador, no la posición, conserva la selección cuando cambia el filtro.
        ids = tabla["customer_id"].astype(str).tolist()
        clave = f"{prefijo}_cliente"
        if st.session_state.get(clave) not in ids:
            st.session_state[clave] = ids[0]
        indice = tabla.assign(_id=tabla["customer_id"].astype(str)).set_index("_id")
        cid = st.selectbox("Cliente de esta vista", ids, key=clave,
                           format_func=lambda identificador: f"{identificador} · vehículo {indice.loc[identificador, 'vehicle_id']}")
        fila = indice.loc[cid]
        st.markdown(f"**{fila['situacion']}** · {fila['motivos_operativos']}")
        a, b, c, d = st.columns(4)
        a.metric("Prioridad global", valor(fila["orden_contacto"]))
        b.metric("Probabilidad de abandono", valor(fila["probabilidad"], 4))
        c.metric("Grupo inicial", fila["grupo"])
        d.metric("Días de margen", valor(fila["dias_restantes"]))
        st.caption(f"Concesionario: {fila['concesionario'] if pd.notna(fila['concesionario']) else 'Sin asignar'}. "
                   f"Vehículo representativo: {fila['vehicle_id']}. Fecha de scoring: {fila['fecha']}.")
        st.markdown("**Los tres principales motivos SHAP**")
        drivers = []
        for numero in (1, 2, 3):
            aporte = fila[f"aporte_SHAP_{numero}"]
            drivers.append({"Motivo": fila[f"motivo_SHAP_{numero}"],
                            "Variable": fila[f"variable_SHAP_{numero}"],
                            "Aporte SHAP": aporte,
                            "Efecto sobre el riesgo": "Sin dato" if pd.isna(aporte) else
                            "Aumenta" if aporte > 0 else "Disminuye" if aporte < 0 else "Sin aporte"})
        st.dataframe(pd.DataFrame(drivers), hide_index=True, width="stretch",
                     column_config={"Motivo": st.column_config.TextColumn(width="large"),
                                    "Aporte SHAP": st.column_config.NumberColumn(format="%+.4f")})
        st.caption("SHAP explica el score del modelo base. Sus aportes no son porcentajes de la probabilidad calibrada.")
        relacionados = candidatos[candidatos["customer_id"].astype("string") == str(cid)]
        st.markdown(f"**Vehículos asociados en Alto + Medio: {miles(len(relacionados))}**")
        st.dataframe(relacionados[["vehicle_id", "grupo", "probabilidad", "estado_contacto", "representante",
                                  "concesionario", "dias_restantes"]], hide_index=True, width="stretch",
                     column_config=configuracion_columnas())
        st.caption("Se contacta una sola vez por cliente. Los grupos, la probabilidad y los motivos de la lista "
                   "pertenecen al vehículo representativo.")


st.caption("Totales de la corrida completa, antes de aplicar los filtros de las listas.")
metricas = st.columns(4)
for columna, etiqueta, campo in zip(metricas,
        ("Seleccionados para contactar", "Elegibles en espera", "Clientes para revisar", "Clientes analizados"),
        ("clientes_seleccionados", "clientes_en_espera", "clientes_revisar", "clientes_identificados")):
    columna.metric(etiqueta, miles(resumen[campo]))

grafico, contexto = st.columns([1.35, 1], gap="large")
with grafico:
    conteos = clientes["situacion"].value_counts().reindex(ESTADOS_CLIENTE, fill_value=0)
    fig = go.Figure(go.Bar(x=conteos.values, y=conteos.index, orientation="h",
                           marker_color=["#1700F3", "#00095B", "#8290AD", "#B6C0D4", "#DCE2EC"],
                           text=[miles(v) for v in conteos.values], textposition="outside",
                           cliponaxis=False, hovertemplate="%{y}: %{x:,.0f} clientes<extra></extra>"))
    estilo_grafico(fig)
    fig.update_layout(height=205, margin=dict(l=0, r=48, t=5, b=5), showlegend=False,
                      xaxis=dict(visible=False), yaxis=dict(autorange="reversed", title=None))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with contexto:
    st.markdown("**Una acción por cliente**")
    st.write(f"La lista reúne los grupos Alto y Medio y aplica el segundo filtro. "
             f"La capacidad de esta corrida es de **{miles(resumen['capacidad_por_corrida'])} clientes**.")
    st.caption("Los elegibles fuera de la capacidad quedan en espera. La prioridad combina señales operativas, "
               "vínculo reciente y riesgo; al filtrar, conserva su orden global.")
    st.caption("La probabilidad de 0 a 1 indica riesgo de abandono. La prioridad no estima el efecto de una llamada.")

operacion, auditoria, inicial = st.tabs(["Contactos", "Auditoría del filtro", "Análisis inicial"])
with operacion:
    vista = filtros(clientes, f"{prefijo}_contactos")
    st.caption(f"{miles(len(vista))} clientes en esta vista. Grupo y concesionario corresponden al vehículo representativo.")
    mostrar_tabla(vista, f"{prefijo}_contactos")
    detalle_cliente(vista)
    with st.expander("Exportar la lista completa de seleccionados"):
        st.caption("Incluye todos los clientes seleccionados de esta corrida, sin aplicar los filtros de la vista.")
        seleccionados = clientes[clientes["seleccionado"]]
        st.download_button("Descargar todos los seleccionados", csv_resultados(seleccionados),
                           file_name=f"seleccionados_{dataset_id}.csv", mime="text/csv",
                           disabled=seleccionados.empty)

with auditoria:
    st.caption("Una fila por vehículo de los grupos Alto y Medio, incluidos los casos sin cliente identificado. "
               "Permite revisar exclusiones y vehículos consolidados bajo un mismo cliente.")
    vista_auditoria = filtros(candidatos, f"{prefijo}_auditoria", auditoria=True)
    st.caption(f"{miles(len(vista_auditoria))} vehículos en esta vista de {miles(len(candidatos))} candidatos.")
    mostrar_tabla(vista_auditoria, f"{prefijo}_auditoria")
    with st.expander("Criterios y alcance de la segunda etapa"):
        politica = resumen["politica"]
        st.write(f"Para ser elegible se requiere cliente identificado, ausencia de turno agendado, "
                 f"al menos {politica['min_dias_restantes']:g} días de margen e historial con concesionario. "
                 "Los datos insuficientes quedan para revisar. El indicador de turno incluye cualquier service pendiente.")
        st.write("Entre los elegibles se prioriza una señal SHAP operativa que aumente el riesgo; luego, "
                 f"mantenimiento en los últimos {politica['max_dias_vinculo_reciente']:g} días, riesgo descendente "
                 "y menor margen restante. Se conserva el mejor vehículo elegible por cliente. "
                 "Una probabilidad de abandono de 1 no es motivo de exclusión.")
        st.caption("Esta política requiere validación operativa. El dataset no confirma teléfono ni permiso de contacto.")
        st.dataframe(pd.DataFrame([
            {"Paso": "Scoring inicial", "Unidad": "Vehículos", "Cantidad": resumen["poblacion_inicial"]},
            {"Paso": "Grupos Alto + Medio", "Unidad": "Vehículos", "Cantidad": resumen["candidatos"]},
            {"Paso": "Sin identificador", "Unidad": "Vehículos", "Cantidad": resumen["vehiculos_sin_identificador"]},
            {"Paso": "Consolidación", "Unidad": "Clientes", "Cantidad": resumen["clientes_identificados"]},
            {"Paso": "Elegibles", "Unidad": "Clientes", "Cantidad": resumen["clientes_elegibles"]},
            {"Paso": "Seleccionados", "Unidad": "Clientes", "Cantidad": resumen["clientes_seleccionados"]},
        ]), hide_index=True, width="stretch")

with inicial:
    segmentos = json.loads(texto(activo()["params"]))["segmentos"]
    st.caption("Scoring de todos los vehículos antes del filtro de contacto. Distribución por ranking: "
               f"Alto {pct(segmentos['top_alto'])}, Medio {pct(segmentos['top_medio'])} y "
               f"Bajo {pct(1 - segmentos['top_alto'] - segmentos['top_medio'])}. "
               "Los valores de SHAP y la probabilidad se conservan en la segunda etapa.")
    tabla_inicial = tabla_completa(scores(), adicionales=True)
    vista_inicial = filtros(tabla_inicial, f"{prefijo}_inicial", inicial=True)
    st.caption(f"{miles(len(vista_inicial))} vehículos en esta vista de {miles(len(tabla_inicial))} analizados.")
    mostrar_tabla(vista_inicial, f"{prefijo}_inicial", inicial=True)
