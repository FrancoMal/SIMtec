"""Segundo paso operativo entre el ranking de riesgo y la lista de contactos.

Usa exclusivamente columnas del scoring existente. Las reglas no aprenden respuesta a
una campaña: mantienen prob_churn y sus explicaciones y dejan una auditoría por vehículo.
La capacidad limita customer_id distintos en una corrida, no vehículos ni un saldo mensual.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[2]
POLICY_PATH = PROJECT_DIR / "config" / "contacto.json"
ESTADOS = ("Contactar", "Con turno", "Sin margen", "Sin identificador", "Revisar")
ARCHIVOS = ("candidatos_contacto.parquet", "candidatos_contacto.csv",
            "contactos_por_cliente.parquet", "contactos_por_cliente.csv", "contacto_resumen.json")


def cargar_politica(policy: dict | None = None) -> dict:
    """Combina la política del proyecto con reemplazos explícitos y valida sus límites."""
    base = json.loads(POLICY_PATH.read_text(encoding="utf8"))
    if policy is not None:
        base.update(deepcopy(policy))
    if not isinstance(base.get("grupos"), list) or not base["grupos"]:
        raise ValueError("La politica necesita una lista no vacia de grupos.")
    if set(base["grupos"]) != {"Alto", "Medio"}:
        raise ValueError("El segundo paso debe tomar exactamente los grupos Alto y Medio.")
    for nombre in ("min_dias_restantes", "max_dias_vinculo_reciente"):
        valor = base.get(nombre)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not np.isfinite(valor) or valor < 0:
            raise ValueError(f"{nombre} debe ser un numero finito no negativo.")
    features = base.get("features_shap_accionables")
    if not isinstance(features, list) or any(not isinstance(f, str) for f in features):
        raise ValueError("features_shap_accionables debe ser una lista de nombres de variables.")
    return base


def _capacidad(policy: dict, capacidad: int | None) -> int:
    if capacidad is None:
        capacidad = policy.get("capacidad_por_corrida")
    if capacidad is None:
        negocio = json.loads((PROJECT_DIR / "config" / "negocio.json").read_text(encoding="utf8"))
        capacidad = negocio.get("capacidad_contactos_mes", 3000)
    if isinstance(capacidad, bool) or not isinstance(capacidad, (int, np.integer)) or capacidad < 0:
        raise ValueError("La capacidad por corrida debe ser un numero entero no negativo.")
    return int(capacidad)


def _columna(df: pd.DataFrame, nombre: str) -> pd.Series:
    return df[nombre] if nombre in df else pd.Series(pd.NA, index=df.index, dtype="object")


def _texto(df: pd.DataFrame, nombre: str) -> pd.Series:
    return _columna(df, nombre).astype("string").str.strip().fillna("")


def _numero(df: pd.DataFrame, nombre: str) -> pd.Series:
    return pd.to_numeric(_columna(df, nombre), errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan)


def _booleano(df: pd.DataFrame, nombre: str) -> pd.Series:
    # No convertir strings con astype(bool): 'False' se convertiría en True.
    return _texto(df, nombre).str.lower().map({"true": True, "false": False, "1": True, "0": False,
                                             "1.0": True, "0.0": False}).astype("boolean")


def generar_contactos(scores: pd.DataFrame, policy: dict | None = None, capacidad: int | None = None
                      ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Devuelve auditoría de Alto+Medio, una fila por cliente identificado y resumen.

    ``estado_contacto == 'Contactar'`` indica elegibilidad. ``seleccionado`` indica
    que el representante del cliente entra en la capacidad; ``en_espera`` identifica
    representantes elegibles fuera de esa capacidad. Los demás vehículos del mismo
    cliente conservan su estado y motivos, con ``representante=False``.
    """
    politica = cargar_politica(policy)
    limite = _capacidad(politica, capacidad)
    politica["capacidad_por_corrida"] = limite
    requeridas = {"customer_id", "vehicle_id", "segmento", "prob_churn", "driver_1", "driver_2", "driver_3"}
    faltan = sorted(requeridas - set(scores.columns))
    if faltan:
        raise ValueError("Faltan columnas del scoring: " + ", ".join(faltan))
    candidatos = scores.loc[scores["segmento"].isin(politica["grupos"])].copy().reset_index(drop=True)
    originales = list(candidatos.columns)
    cliente = _texto(candidatos, "customer_id")
    vehiculo = _texto(candidatos, "vehicle_id")
    dealer = _texto(candidatos, "last_maint_dealer")
    margen = _numero(candidatos, "dias_restantes_horizonte")
    historia = _numero(candidatos, "n_maint")
    recencia = _numero(candidatos, "days_since_last_maint")
    probabilidad = _numero(candidatos, "prob_churn")
    turno = _booleano(candidatos, "tiene_turno_agendado")

    accionables = set(politica["features_shap_accionables"])
    senales: list[list[str]] = [[] for _ in range(len(candidatos))]
    for numero in (1, 2, 3):
        feature = _texto(candidatos, f"driver_{numero}_feature")
        aporte = _numero(candidatos, f"driver_{numero}_shap")
        positivo = feature.isin(accionables) & aporte.gt(0)
        for posicion in np.flatnonzero(positivo.to_numpy()):
            if feature.iloc[posicion] not in senales[posicion]:
                senales[posicion].append(feature.iloc[posicion])

    estados, motivos = [], []
    for pos in range(len(candidatos)):
        razones: list[str] = []
        sin_id = not cliente.iloc[pos]
        con_turno = bool(turno.iloc[pos]) if pd.notna(turno.iloc[pos]) else False
        sin_margen = pd.notna(margen.iloc[pos]) and margen.iloc[pos] < politica["min_dias_restantes"]
        datos = []
        if not vehiculo.iloc[pos]:
            datos.append("vehicle_id")
        if pd.isna(turno.iloc[pos]):
            datos.append("estado del turno")
        if pd.isna(margen.iloc[pos]):
            datos.append("dias restantes")
        if pd.isna(historia.iloc[pos]) or historia.iloc[pos] < 0:
            datos.append("historia de mantenimiento")
        if pd.isna(probabilidad.iloc[pos]) or not 0 <= probabilidad.iloc[pos] <= 1:
            datos.append("probabilidad de churn valida")
        if sin_id:
            razones.append("Falta customer_id: resolver la identidad antes de contactar.")
        if con_turno:
            razones.append("Tiene un turno pendiente registrado: coordinar seguimiento antes de un nuevo contacto.")
        if sin_margen:
            razones.append(f"Quedan {margen.iloc[pos]:g} dias: menos que el minimo operativo de {politica['min_dias_restantes']:g}.")
        if datos:
            razones.append("Revisar datos insuficientes: " + ", ".join(datos) + ".")
        if pd.notna(historia.iloc[pos]) and historia.iloc[pos] == 0:
            razones.append("Sin mantenimiento previo registrado: revisar el vinculo con la red.")
        if not dealer.iloc[pos]:
            razones.append("Sin concesionario de mantenimiento asignado: resolver la derivacion.")

        # La precedencia da un estado único; motivos conserva todas las causas detectadas.
        if sin_id:
            estado = "Sin identificador"
        elif con_turno:
            estado = "Con turno"
        elif sin_margen:
            estado = "Sin margen"
        elif datos or historia.iloc[pos] <= 0 or not dealer.iloc[pos]:
            estado = "Revisar"
        else:
            estado = "Contactar"
            razones.append("Cliente identificado, sin turno pendiente, con margen, historia y concesionario de mantenimiento.")
        if senales[pos]:
            razones.append("SHAP positivo orienta una accion sobre: " + ", ".join(senales[pos]) + ".")
        else:
            razones.append("Sin senal SHAP orientable a una accion entre los tres motivos principales; no es un descarte.")
        if pd.notna(recencia.iloc[pos]) and 0 <= recencia.iloc[pos] <= politica["max_dias_vinculo_reciente"]:
            razones.append(f"Vinculo reciente: ultimo mantenimiento hace {recencia.iloc[pos]:g} dias.")
        else:
            razones.append("No consta un mantenimiento dentro del limite de vinculo reciente; no es un descarte.")
        estados.append(estado)
        motivos.append(" ".join(razones))

    candidatos["estado_contacto"] = pd.Series(estados, dtype="string")
    candidatos["motivos_operativos"] = pd.Series(motivos, dtype="string")
    candidatos["shap_accionable"] = pd.Series([bool(s) for s in senales], dtype=bool)
    candidatos["vinculo_reciente"] = recencia.between(0, politica["max_dias_vinculo_reciente"])
    candidatos["_cliente"] = cliente
    candidatos["_vehiculo"] = vehiculo
    candidatos["_elegible"] = candidatos["estado_contacto"].eq("Contactar")
    candidatos["_probabilidad"] = probabilidad
    candidatos["_margen"] = margen
    candidatos = candidatos.sort_values(
        ["_elegible", "shap_accionable", "vinculo_reciente", "_probabilidad", "_margen", "_cliente", "_vehiculo"],
        ascending=[False, False, False, False, True, True, True], na_position="last", kind="stable",
    ).reset_index(drop=True)
    candidatos["representante"] = candidatos["_cliente"].ne("") & ~candidatos["_cliente"].duplicated()
    representantes_elegibles = candidatos["representante"] & candidatos["_elegible"]
    candidatos["orden_contacto"] = pd.Series(pd.NA, index=candidatos.index, dtype="Int64")
    candidatos.loc[representantes_elegibles, "orden_contacto"] = np.arange(1, int(representantes_elegibles.sum()) + 1)
    candidatos["seleccionado"] = candidatos["orden_contacto"].le(limite).fillna(False).astype(bool)
    candidatos["en_espera"] = representantes_elegibles & ~candidatos["seleccionado"]

    identificados = candidatos[candidatos["_cliente"].ne("")]
    vehiculos = identificados.groupby("_cliente", sort=False)["_vehiculo"].agg(lambda x: " | ".join(sorted(set(x) - {""})))
    n_vehiculos = identificados.groupby("_cliente", sort=False)["_vehiculo"].agg(lambda x: len(set(x) - {""}))
    grupos = identificados.groupby("_cliente", sort=False)["segmento"].agg(
        lambda x: " | ".join(g for g in ("Alto", "Medio") if g in set(x)))
    candidatos["vehiculos_cliente"] = candidatos["_cliente"].map(vehiculos).fillna(candidatos["_vehiculo"])
    candidatos["n_vehiculos_cliente"] = candidatos["_cliente"].map(n_vehiculos).fillna(0).astype(int)
    candidatos["grupos_cliente"] = candidatos["_cliente"].map(grupos).fillna(candidatos["segmento"].astype("string"))
    # Sólo hay una acción por cliente: los duplicados no consumen capacidad y se ven en auditoría.
    clientes = candidatos[candidatos["representante"]].copy().reset_index(drop=True)
    internas = ["_cliente", "_vehiculo", "_elegible", "_probabilidad", "_margen"]
    candidatos = candidatos.drop(columns=internas)
    clientes = clientes.drop(columns=internas)
    resumen: dict[str, Any] = {
        "version": 1,
        "tipo": "priorizacion_operativa_sin_modelo_de_respuesta",
        "politica": politica,
        "capacidad_por_corrida": limite,
        "poblacion_inicial": int(len(scores)),
        "candidatos": int(len(candidatos)),
        "grupos_origen": {g: int(candidatos["segmento"].eq(g).sum()) for g in politica["grupos"]},
        "fuera_de_alcance": int(len(scores) - len(candidatos)),
        "clientes_identificados": int(len(clientes)),
        "clientes_elegibles": int(clientes["estado_contacto"].eq("Contactar").sum()),
        "clientes_seleccionados": int(clientes["seleccionado"].sum()),
        "clientes_en_espera": int(clientes["en_espera"].sum()),
        "clientes_revisar": int(clientes["estado_contacto"].eq("Revisar").sum()),
        "vehiculos_sin_identificador": int(candidatos["estado_contacto"].eq("Sin identificador").sum()),
        "vehiculos_unificados": int((candidatos["customer_id"].astype("string").str.strip().fillna("").ne("")
                                      & ~candidatos["representante"]).sum()),
        "estados_vehiculos": {e: int(candidatos["estado_contacto"].eq(e).sum()) for e in ESTADOS},
        "estados_clientes": {e: int(clientes["estado_contacto"].eq(e).sum()) for e in ESTADOS},
        "columnas_originales": originales,
        "interpretacion": "prob_churn y los tres motivos SHAP explican riesgo de no completar mantenimiento; "
                          "la seleccion aplica reglas operativas y no estima probabilidad de recuperacion ni uplift.",
        "alcance_vehiculos_cliente": "Los vehiculos y grupos consolidados corresponden a los candidatos Alto y Medio.",
    }
    return candidatos, clientes, resumen


def guardar_contactos(scores: pd.DataFrame, output_dir: str | Path, policy: dict | None = None,
                       capacidad: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Guarda los cinco artefactos en una carpeta processed del conjunto elegido."""
    candidatos, clientes, resumen = generar_contactos(scores, policy, capacidad)
    destino = Path(output_dir)
    destino.mkdir(parents=True, exist_ok=True)
    resumen["generado_en_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fuente = destino / "scores_actuales.parquet"
    resumen["scores_sha256"] = None
    if fuente.is_file():
        with fuente.open("rb") as archivo:
            resumen["scores_sha256"] = hashlib.file_digest(archivo, "sha256").hexdigest()
    resumen["scores_archivo"] = "scores_actuales.parquet"
    # Preparar todo antes de sustituir la entrega. El resumen se publica último:
    # su ausencia invalida resultados parciales incluso si scores no cambió.
    corrida = uuid.uuid4().hex
    temporales = {nombre: destino / f".{nombre}.{corrida}.tmp" for nombre in ARCHIVOS}
    try:
        for nombre, tabla in (("candidatos_contacto", candidatos), ("contactos_por_cliente", clientes)):
            tabla.to_parquet(temporales[f"{nombre}.parquet"], index=False)
            tabla.to_csv(temporales[f"{nombre}.csv"], index=False, encoding="utf-8-sig")
        temporales["contacto_resumen.json"].write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf8")
        (destino / "contacto_resumen.json").unlink(missing_ok=True)
        for nombre in ARCHIVOS:
            temporales[nombre].replace(destino / nombre)
    finally:
        for temporal in temporales.values():
            temporal.unlink(missing_ok=True)
    return candidatos, clientes, resumen
