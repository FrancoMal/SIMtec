"""Vistas y filtros de la lista operativa, sin alterar decisiones del modelo."""
from __future__ import annotations

import pandas as pd

from lib.listado import tabla_contactos


SIN_CONCESIONARIO = "Sin concesionario"
ESTADOS_CLIENTE = ["Seleccionado", "En espera", "Revisar", "Con turno", "Sin margen"]


def preparar_contactos(datos: pd.DataFrame) -> pd.DataFrame:
    """Añade una etiqueta de situación y conserva el orden global de la corrida."""
    tabla = tabla_contactos(datos, adicionales=True)
    tabla["situacion"] = tabla["estado_contacto"].astype("string")
    tabla.loc[tabla["seleccionado"].fillna(False), "situacion"] = "Seleccionado"
    tabla.loc[tabla["en_espera"].fillna(False), "situacion"] = "En espera"
    tabla.loc[(tabla["estado_contacto"] == "Contactar")
              & ~tabla["representante"].fillna(False), "situacion"] = "Otro vehículo representa al cliente"
    return tabla


def concesionarios(tabla: pd.DataFrame) -> pd.Series:
    return tabla["concesionario"].astype("string").str.strip().replace("", pd.NA).fillna(SIN_CONCESIONARIO)


def filtrar_resultados(tabla: pd.DataFrame, *, situacion: str = "Todos", grupo: str = "Todos",
                       concesionario: str = "Todos", busqueda: str = "") -> pd.DataFrame:
    """Combina filtros; busca también en los vehículos asociados del mismo cliente."""
    mascara = pd.Series(True, index=tabla.index)
    if situacion != "Todos":
        mascara &= tabla["situacion"].eq(situacion).fillna(False)
    if grupo != "Todos":
        mascara &= tabla["grupo"].eq(grupo).fillna(False)
    if concesionario != "Todos":
        mascara &= concesionarios(tabla).eq(concesionario)
    consulta = busqueda.strip()
    if consulta:
        coincide = pd.Series(False, index=tabla.index)
        for columna in ("customer_id", "vehicle_id", "vehiculos_cliente"):
            if columna in tabla:
                coincide |= tabla[columna].astype("string").str.contains(
                    consulta, case=False, regex=False, na=False)
        mascara &= coincide
    return tabla.loc[mascara].copy()


def csv_resultados(tabla: pd.DataFrame) -> bytes:
    """Exporta exactamente las filas y el orden de la vista, con todos sus datos."""
    return tabla.to_csv(index=False, float_format="%.8f").encode("utf-8-sig")
